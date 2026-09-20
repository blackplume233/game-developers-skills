#!/usr/bin/env python3
"""Validate Windows Terminal settings.json against the schema for the version actually installed.

Why this exists: settings key names, enum values and whole feature areas change
between Windows Terminal releases, and a key that the installed version does not
know is silently ignored - the setting simply does not apply, with no error
anywhere. Guessing a key name from memory, a blog post, or a newer release's
docs is how you end up debugging a setting that was never in effect.

This checks two things, both against the version-matched schema:

  * syntax - the file is JSONC (comments and trailing commas allowed), and it
    parses once they are removed. Comments are blanked rather than deleted so
    reported line/column numbers still point at the real line.
  * conformance - every key exists in the schema at that position, every value
    is legal for its enum/const, values are of the right type, and keys the
    schema marks deprecated are reported separately.

It is deliberately not a general JSON Schema implementation: it resolves $ref,
flattens allOf/anyOf/oneOf into candidate branches and checks keys/values
against those. That covers exactly the failure mode described above.

Usage:
    python validate-settings.py                       # auto-detect settings and version
    python validate-settings.py --settings PATH       # explicit file
    python validate-settings.py --version 1.24.11911.0
    python validate-settings.py --schema PATH_OR_URL --offline
    python validate-settings.py --json

Exit codes: 0 clean, 1 problems found, 2 could not run (no settings / no schema).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

SCHEMA_URL = "https://raw.githubusercontent.com/microsoft/terminal/v{version}/doc/cascadia/profiles.schema.json"


# ---------------------------------------------------------------- settings file

def find_settings() -> list[str]:
    """Candidate settings.json paths, most likely first."""
    local = os.environ.get("LOCALAPPDATA", "")
    cands: list[str] = []
    if local:
        cands += sorted(glob.glob(os.path.join(local, "Packages", "Microsoft.WindowsTerminal*",
                                               "LocalState", "settings.json")), reverse=True)
        cands.append(os.path.join(local, "Microsoft", "Windows Terminal", "settings.json"))
    return [p for p in cands if os.path.isfile(p)]


def installed_version() -> str | None:
    """Version of the installed Windows Terminal package, or None."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-AppxPackage Microsoft.WindowsTerminal | Select-Object -First 1).Version.ToString()"],
            capture_output=True, text=True, timeout=60)
        ver = out.stdout.strip()
        return ver or None
    except (OSError, subprocess.SubprocessError):
        return None


# ------------------------------------------------------------------------ JSONC

def blank_jsonc(text: str) -> str:
    """Remove comments and trailing commas, preserving offsets and line numbers."""
    out: list[str] = []
    i, n, in_str = 0, len(text), False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] not in "\r\n":
                out.append(" ")
                i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            end = n if j < 0 else j + 2
            for ch in text[i:end]:
                out.append("\n" if ch == "\n" else " ")
            i = end
            continue
        out.append(c)
        i += 1
    stripped = "".join(out)
    return re.sub(r",(\s*[}\]])", r"\1", stripped)


# ---------------------------------------------------------------------- schema

UNION_KEYS = ("allOf", "anyOf", "oneOf")


def _resolve(ref: str, root: dict) -> dict:
    target: object = root
    try:
        for part in ref.lstrip("#/").split("/"):
            target = target[part]  # type: ignore[index]
    except (KeyError, TypeError):
        return {}
    return target if isinstance(target, dict) else {}


def deref(node: object, root: dict) -> list[dict]:
    """Flatten a schema node into a list of candidate nodes.

    A node's own constraints have to survive alongside its union keywords: the
    Keybinding definition, for instance, carries `properties` AND an `anyOf`
    whose branches only list `required` keys. Expanding the union alone would
    throw the properties away and report every legal key as unknown.
    """
    if not isinstance(node, dict):
        return [node] if node else []
    out: list[dict] = []
    if "$ref" in node:
        out.extend(deref(_resolve(node["$ref"], root), root))
    branches: list[dict] = []
    for key in UNION_KEYS:
        for sub in node.get(key) or []:
            branches.extend(deref(sub, root))
    out.extend(branches)
    own = {k: v for k, v in node.items() if k not in UNION_KEYS and k != "$ref"}
    if out:
        if own:
            out.append(own)
    else:
        out.append(own or node)
    return out


def candidates_for(node: dict, root: dict) -> list[dict]:
    return deref(node, root) if isinstance(node, dict) else []


def walk_settings(value, schema_node: dict, root: dict, path: str, problems: list, checked: list,
                  unrecognised: list, deprecated: list) -> None:
    cands = candidates_for(schema_node, root)
    if not cands:
        return

    if isinstance(value, dict):
        # A key can be described by several candidate branches at once (a
        # newTabMenu entry's `type` is a different const in each branch), so
        # collect every candidate spec per key instead of letting the last
        # branch overwrite the others. Keys may also be matched by
        # patternProperties rather than named - font.features is one, where any
        # four printable ASCII characters name an OpenType feature tag.
        prop_map: dict[str, list[dict]] = {}
        patterns: list[tuple[re.Pattern, dict]] = []
        forbids_extra = False
        for c in cands:
            for k, v in (c.get("properties") or {}).items():
                prop_map.setdefault(k, []).append(v)
            for pat, v in (c.get("patternProperties") or {}).items():
                try:
                    patterns.append((re.compile(pat), v))
                except re.error:
                    pass
            if c.get("additionalProperties") is False:
                forbids_extra = True
            elif isinstance(c.get("additionalProperties"), dict):
                prop_map.setdefault("*", []).append(c["additionalProperties"])

        for key, sub in value.items():
            child_path = f"{path}.{key}" if path else key
            specs = prop_map.get(key) or prop_map.get("*")
            if specs is None:
                specs = [v for pat, v in patterns if pat.search(key)] or None
            if specs is None:
                if not path and key in ("$schema", "$help"):
                    checked.append(child_path)   # JSON conventions, not terminal settings
                    continue
                if forbids_extra:
                    problems.append((child_path, "unknown key - the schema for this version does not allow it here"))
                else:
                    unrecognised.append((child_path, "key is not defined for this version; the terminal ignores it"))
                continue
            checked.append(child_path)
            for spec in specs:
                if isinstance(spec, dict) and spec.get("deprecated"):
                    deprecated.append((child_path, str(spec.get("description", "deprecated")).splitlines()[0][:110]))
                    break
            walk_settings(sub, {"anyOf": specs}, root, child_path, problems, checked,
                          unrecognised, deprecated)
        return

    if isinstance(value, list):
        item_specs: list[dict] = []
        for c in cands:
            if isinstance(c.get("items"), dict):
                item_specs.append(c["items"])
            if isinstance(c.get("prefixItems"), list):
                item_specs.extend(c["prefixItems"])
        if item_specs:
            for idx, item in enumerate(value):
                walk_settings(item, {"anyOf": item_specs}, root, f"{path}[{idx}]", problems, checked,
                              unrecognised, deprecated)
        return

    # scalars: enum / const / type
    type_err = None
    ok = False
    for c in cands:
        enum = c.get("enum")
        const = c.get("const")
        ctype = c.get("type")
        if enum is not None and value not in enum:
            type_err = f"value {value!r} is not one of {enum}"
            continue
        if const is not None and value != const:
            type_err = f"value {value!r} must be {const!r}"
            continue
        if ctype and not _type_matches(value, ctype):
            type_err = f"value {value!r} is not of type {ctype}"
            continue
        ok = True
        break
    if not ok and type_err:
        problems.append((path, type_err))


def _type_matches(value, ctype) -> bool:
    if isinstance(ctype, list):
        return any(_type_matches(value, t) for t in ctype)
    return {
        "string": lambda v: isinstance(v, str),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "null": lambda v: v is None,
    }.get(ctype, lambda v: True)(value)


# ------------------------------------------------------------------------ main

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--settings", help="settings.json to check (default: auto-detect)")
    ap.add_argument("--version", help="Windows Terminal version to fetch the schema for")
    ap.add_argument("--schema", help="schema file path or URL (skips version detection)")
    ap.add_argument("--cache-dir", default=os.path.join(tempfile.gettempdir(), "wt-settings-schema"))
    ap.add_argument("--offline", action="store_true", help="never download; use the cache only")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    settings_path = args.settings
    if not settings_path:
        found = find_settings()
        if not found:
            print("error: no Windows Terminal settings.json found; pass --settings PATH", file=sys.stderr)
            return 2
        settings_path = found[0]
    if not os.path.isfile(settings_path):
        print(f"error: {settings_path} does not exist", file=sys.stderr)
        return 2

    version = args.version or installed_version()
    label = f"v{version}" if version else "main (installed version unknown)"
    if args.schema:
        schema_src = args.schema
    elif version:
        schema_src = SCHEMA_URL.format(version=version)
    else:
        schema_src = SCHEMA_URL.format(version="main")

    os.makedirs(args.cache_dir, exist_ok=True)
    cache_name = re.sub(r"[^A-Za-z0-9._-]", "_", ("schema-" + (version or "main")) + ".json")
    cache_path = os.path.join(args.cache_dir, cache_name)

    if os.path.isfile(schema_src):
        with open(schema_src, encoding="utf-8") as fh:
            schema_text = fh.read()
    elif os.path.isfile(cache_path):
        with open(cache_path, encoding="utf-8") as fh:
            schema_text = fh.read()
        label += " (cached schema)"
    elif args.offline:
        print(f"error: no cached schema at {cache_path} and --offline was given", file=sys.stderr)
        return 2
    else:
        try:
            with urllib.request.urlopen(schema_src, timeout=30) as resp:  # noqa: S310 - fixed https URL
                schema_text = resp.read().decode("utf-8")
        except Exception as exc:  # noqa: BLE001 - surfaced verbatim to the user
            print(f"error: could not fetch schema {schema_src}: {exc}\n"
                  f"       hint: --schema PATH, or --cache-dir with a cached copy", file=sys.stderr)
            return 2
        with open(cache_path, "w", encoding="utf-8", newline="") as fh:
            fh.write(schema_text)

    schema = json.loads(schema_text)
    with open(settings_path, encoding="utf-8") as fh:
        raw = fh.read()

    problems: list[tuple[str, str]] = []
    deprecated: list[tuple[str, str]] = []
    unrecognised: list[tuple[str, str]] = []
    checked: list[str] = []

    try:
        settings = json.loads(blank_jsonc(raw))
    except json.JSONDecodeError as exc:
        problems.append((f"line {exc.lineno} col {exc.colno}", f"invalid JSON/JSONC: {exc.msg}"))
        settings = None

    if settings is not None:
        walk_settings(settings, schema, schema, "", problems, checked, unrecognised, deprecated)

    if args.json:
        print(json.dumps({"settings": settings_path, "schema": label, "problems": problems,
                          "deprecated": deprecated, "unrecognised": unrecognised,
                          "keys_checked": len(checked)}, indent=2))
    else:
        print(f"settings : {settings_path}")
        print(f"schema   : {label}")
        print(f"checked  : {len(checked)} keys")
        if problems:
            print(f"\nPROBLEMS ({len(problems)}):")
            for where, what in problems:
                print(f"  - {where}: {what}")
        if unrecognised:
            print(f"\nNOT IN THIS VERSION ({len(unrecognised)}) - the terminal will ignore these:")
            for where, what in unrecognised:
                print(f"  - {where}: {what}")
        if deprecated:
            print(f"\nDEPRECATED ({len(deprecated)}):")
            for where, what in deprecated:
                print(f"  - {where}: {what}")
        if not problems and not unrecognised and not deprecated:
            print("\nresult   : OK - every key and value is known to this version")
        elif problems:
            print("\nresult   : PROBLEMS FOUND")
        else:
            print("\nresult   : OK, with notes above")

    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
