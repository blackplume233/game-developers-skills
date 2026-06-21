#!/usr/bin/env python3
"""Search local skills and referenced skill repositories."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class Skill:
    scope: str
    source: str
    name: str
    version: str
    description: str
    path: str


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists() and (candidate / "skills").is_dir():
            return candidate
    return current


def parse_frontmatter(skill_file: Path) -> dict[str, str]:
    text = skill_file.read_text(encoding="utf-8", errors="replace")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}

    data: dict[str, str] = {}
    active_key: str | None = None
    for raw_line in match.group(1).splitlines():
        if raw_line.startswith((" ", "\t")) and active_key:
            data[active_key] = f"{data[active_key]} {raw_line.strip()}".strip()
            continue

        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        active_key = key.strip()
        value = value.strip().strip("'\"")
        if value in {">-", "|-"}:
            value = ""
        data[active_key] = value
    return data


def skill_from_file(repo_root: Path, skill_file: Path, scope: str, source: str) -> Skill:
    data = parse_frontmatter(skill_file)
    return Skill(
        scope=scope,
        source=source,
        name=data.get("name", skill_file.parent.name),
        version=data.get("version", "unknown"),
        description=" ".join(data.get("description", "").split()),
        path=skill_file.relative_to(repo_root).as_posix(),
    )


def iter_skill_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.rglob("SKILL.md"))


def collect_skills(repo_root: Path) -> list[Skill]:
    seen: set[Path] = set()
    skills: list[Skill] = []

    for skill_file in iter_skill_files(repo_root / "skills"):
        resolved = skill_file.resolve()
        seen.add(resolved)
        skills.append(skill_from_file(repo_root, skill_file, "local", "skills"))

    reference_roots = [repo_root / "references"]
    reference_roots.extend(repo_root.glob("skills/*/*/references"))

    for references_dir in reference_roots:
        if not references_dir.is_dir():
            continue
        for reference in sorted(path for path in references_dir.iterdir() if path.is_dir()):
            for skill_file in iter_skill_files(reference):
                resolved = skill_file.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                skills.append(
                    skill_from_file(
                        repo_root,
                        skill_file,
                        "reference",
                        reference.name,
                    )
                )

    return skills


def matches(skill: Skill, query: str) -> bool:
    if not query:
        return True
    haystack = " ".join(
        [skill.name, skill.version, skill.description, skill.path, skill.source]
    ).lower()
    return all(token.lower() in haystack for token in query.split())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search skills in this repository and references/* submodules."
    )
    parser.add_argument("query", nargs="*", help="Search terms")
    parser.add_argument("--repo-root", help="Skill repository root; defaults to cwd ancestor")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    repo_root = find_repo_root(Path(args.repo_root or os.getcwd()))
    query = " ".join(args.query).strip()
    skills = [skill for skill in collect_skills(repo_root) if matches(skill, query)]

    if args.json:
        print(json.dumps([asdict(skill) for skill in skills], ensure_ascii=False, indent=2))
        return 0

    if not skills:
        print("No matching skills found.")
        return 1

    for skill in skills:
        suffix = f" - {skill.description}" if skill.description else ""
        print(f"[{skill.scope}:{skill.source}] {skill.name} v{skill.version}{suffix}")
        print(f"  path: {skill.path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
