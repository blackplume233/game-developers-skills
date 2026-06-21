#!/usr/bin/env python3
"""Add an external skill repository as a git submodule under references/."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists() and (candidate / "skills").is_dir():
            return candidate
    return current


def slug_from_source(source: str) -> str:
    normalized = source.rstrip("/\\")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    name = Path(normalized).name
    if not name:
        name = re.sub(r"^.*[:/]", "", normalized)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-_")
    if not slug:
        raise ValueError(f"Cannot derive a reference name from: {source}")
    return slug


def parse_frontmatter(skill_file: Path) -> dict[str, str]:
    text = skill_file.read_text(encoding="utf-8", errors="replace")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    data: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("'\"")
    return data


def discover_skills(reference_path: Path) -> list[tuple[str, str, str, Path]]:
    skill_files = sorted(reference_path.rglob("SKILL.md"))
    discovered: list[tuple[str, str, str, Path]] = []
    for skill_file in skill_files:
        data = parse_frontmatter(skill_file)
        name = data.get("name", skill_file.parent.name)
        version = data.get("version", "unknown")
        description = data.get("description", "").strip()
        discovered.append((name, version, description, skill_file))
    return discovered


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add an external skill repository as references/<name>."
    )
    parser.add_argument("source", help="Git URL or local repository path")
    parser.add_argument("--repo-root", help="Skill repository root; defaults to cwd ancestor")
    parser.add_argument("--name", help="Reference directory name; defaults to source repo name")
    parser.add_argument("--branch", help="Optional branch to track")
    args = parser.parse_args()

    repo_root = find_repo_root(Path(args.repo_root or os.getcwd()))
    references_dir = repo_root / "references"
    ref_name = args.name or slug_from_source(args.source)
    ref_path = references_dir / ref_name
    relative_ref_path = Path("references") / ref_name

    if ref_path.exists():
        print(f"Reference already exists: {relative_ref_path}", file=sys.stderr)
        return 2

    references_dir.mkdir(exist_ok=True)

    source_path = Path(args.source).expanduser()
    is_local_source = source_path.exists()
    source = str(source_path.resolve()) if is_local_source else args.source

    command = ["git"]
    if is_local_source:
        command.extend(["-c", "protocol.file.allow=always"])
    command.extend(["submodule", "add"])
    if args.branch:
        command.extend(["--branch", args.branch])
    command.extend([source, relative_ref_path.as_posix()])

    result = run(command, repo_root)
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout)
        return result.returncode

    update = run(
        ["git", "submodule", "update", "--init", "--recursive", relative_ref_path.as_posix()],
        repo_root,
    )
    if update.returncode != 0:
        sys.stderr.write(update.stderr or update.stdout)
        return update.returncode

    print(f"Added reference repository: {relative_ref_path}")
    skills = discover_skills(ref_path)
    if not skills:
        print("No SKILL.md files found in the referenced repository.")
        return 0

    print("Discovered skills:")
    for name, version, description, skill_file in skills:
        rel_skill_file = skill_file.relative_to(repo_root).as_posix()
        suffix = f" - {description}" if description else ""
        print(f"- {name} v{version}{suffix}")
        print(f"  path: {rel_skill_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
