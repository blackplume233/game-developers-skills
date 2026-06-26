#!/usr/bin/env python3
"""Read, update, and migrate Auto Goal state frontmatter.

Preferred state format:

---
status: active
---
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SECTION_ALIASES = {
    "state": ["状态", "State"],
}

STATE_FIELD_LABEL = "字段"
STATE_VALUE_LABEL = "值"
FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n([\s\S]*?)\n---\s*(?:\n|\Z)", re.MULTILINE)


def heading_pattern(heading: str) -> str:
    return re.escape(heading).replace(r"\ ", r"\s+")


def section_pattern(section_key: str) -> re.Pattern[str]:
    aliases = SECTION_ALIASES[section_key]
    heading_alternatives = "|".join(heading_pattern(alias) for alias in aliases)
    return re.compile(
        rf"(^##\s+(?:{heading_alternatives})\s*$)([\s\S]*?)(?=^##\s+|\Z)",
        re.MULTILINE,
    )


def state_body(text: str) -> str:
    match = section_pattern("state").search(text)
    return match.group(2).strip() if match else ""


def split_frontmatter(text: str) -> tuple[str, str] | None:
    match = FRONTMATTER_PATTERN.match(text)
    if not match:
        return None
    return match.group(1).strip(), text[match.end() :]


def split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in stripped[1:-1]:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "|":
            cells.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    cells.append("".join(current).strip())
    return cells


def is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def unescape_cell(value: str) -> str:
    return value.replace(r"\|", "|").replace(r"\\", "\\").strip()


def escape_cell(value: object) -> str:
    text = "" if value is None else str(value)
    return text.replace("\\", r"\\").replace("|", r"\|").replace("\r", " ").replace("\n", " ").strip()


def parse_markdown_table(body: str) -> dict[str, str]:
    rows = [split_markdown_row(line) for line in body.splitlines()]
    rows = [row for row in rows if row]
    if len(rows) < 2:
        return {}

    header = [cell.strip().lower() for cell in rows[0]]
    if len(header) < 2 or not is_separator_row(rows[1]):
        return {}

    key_index = 0
    value_index = 1
    state: dict[str, str] = {}
    for row in rows[2:]:
        if len(row) <= max(key_index, value_index):
            continue
        key = unescape_cell(row[key_index])
        value = unescape_cell(row[value_index])
        if key:
            state[key] = value
    return state


def parse_yamlish_state(body: str) -> dict[str, str]:
    body = re.sub(r"^```(?:yaml|yml)?\s*$", "", body, flags=re.MULTILINE)
    body = re.sub(r"^```\s*$", "", body, flags=re.MULTILINE)
    state: dict[str, str] = {}
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        state[key.strip()] = unquote_yaml_scalar(value.strip())
    return state


def unquote_yaml_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1].replace(r"\"", '"').replace(r"\\", "\\")
    return value


def render_yaml_scalar(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r", " ").replace("\n", " ").strip()
    if text == "":
        return '""'
    if re.search(r"(^[>|@`!&*{}\[\],#]|:\s|\s#|['\"])", text):
        return "'" + text.replace("'", "''") + "'"
    return text


def parse_state(text: str) -> dict[str, str]:
    frontmatter = split_frontmatter(text)
    if frontmatter:
        state = parse_yamlish_state(frontmatter[0])
        if state:
            return state
    body = state_body(text)
    return parse_markdown_table(body) or parse_yamlish_state(body)


def render_state_frontmatter(state: dict[str, str], key_order: list[str] | None = None) -> str:
    ordered_keys: list[str] = []
    for key in key_order or []:
        if key in state and key not in ordered_keys:
            ordered_keys.append(key)
    for key in state:
        if key not in ordered_keys:
            ordered_keys.append(key)

    lines = ["---"]
    for key in ordered_keys:
        lines.append(f"{key}: {render_yaml_scalar(state[key])}")
    lines.append("---")
    return "\n".join(lines)


def render_state_table(state: dict[str, str], key_order: list[str] | None = None) -> str:
    ordered_keys: list[str] = []
    for key in key_order or []:
        if key in state and key not in ordered_keys:
            ordered_keys.append(key)
    for key in state:
        if key not in ordered_keys:
            ordered_keys.append(key)

    lines = [
        f"| {STATE_FIELD_LABEL} | {STATE_VALUE_LABEL} |",
        "|---|---|",
    ]
    for key in ordered_keys:
        lines.append(f"| {escape_cell(key)} | {escape_cell(state[key])} |")
    return "\n".join(lines)


def replace_state(text: str, state: dict[str, str], key_order: list[str] | None = None) -> str:
    frontmatter = render_state_frontmatter(state, key_order)
    body = section_pattern("state").sub("", text, count=1).lstrip()
    existing = split_frontmatter(body)
    if existing:
        body = existing[1].lstrip()
    return frontmatter + "\n\n" + body


def read_state(path: Path) -> dict[str, str]:
    return parse_state(path.read_text(encoding="utf-8"))


def write_state(path: Path, state: dict[str, str], key_order: list[str] | None = None) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(replace_state(text, state, key_order), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Read or update Auto Goal YAML frontmatter state.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    read_parser = subparsers.add_parser("read", help="Print all state fields as JSON.")
    read_parser.add_argument("goal_file")

    get_parser = subparsers.add_parser("get", help="Print a single state value.")
    get_parser.add_argument("goal_file")
    get_parser.add_argument("key")

    set_parser = subparsers.add_parser("set", help="Set one state value and rewrite the state as a Markdown table.")
    set_parser.add_argument("goal_file")
    set_parser.add_argument("key")
    set_parser.add_argument("value")
    set_parser.add_argument("--in-place", action="store_true", help="Write back to goal_file.")

    migrate_parser = subparsers.add_parser("migrate", help="Rewrite existing state as a Markdown table.")
    migrate_parser.add_argument("goal_file")
    migrate_parser.add_argument("--in-place", action="store_true", help="Write back to goal_file.")

    args = parser.parse_args()
    path = Path(args.goal_file)
    if not path.exists():
        print(json.dumps({"valid": False, "errors": [f"文件不存在：{path}"]}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    state = read_state(path)
    if args.command == "read":
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0
    if args.command == "get":
        if args.key not in state:
            return 1
        print(state[args.key])
        return 0
    if args.command == "set":
        state[args.key] = args.value
        rendered = replace_state(path.read_text(encoding="utf-8"), state)
        if args.in_place:
            path.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    if args.command == "migrate":
        rendered = replace_state(path.read_text(encoding="utf-8"), state)
        if args.in_place:
            path.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
