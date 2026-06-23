#!/usr/bin/env python3
"""Require README and Wiki updates when repository behavior changes."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_IGNORES = {
    "CHANGELOG.md",
}


def run_git(args: list[str], repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def find_repo_root(start: Path) -> Path:
    result = run_git(["rev-parse", "--show-toplevel"], start)
    if result.returncode == 0:
        return Path(result.stdout.strip()).resolve()
    return start.resolve()


def changed_files(repo_root: Path, base: str) -> set[str]:
    commands = [
        ["diff", "--name-only", base, "--"],
        ["diff", "--cached", "--name-only", "--"],
        ["ls-files", "--others", "--exclude-standard"],
    ]
    files: set[str] = set()
    for command in commands:
        result = run_git(command, repo_root)
        if result.returncode != 0:
            sys.stderr.write(result.stderr or result.stdout)
            raise SystemExit(result.returncode)
        files.update(line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip())
    return files


def is_doc_only(path: str, readme: str, wiki: str) -> bool:
    if path in {readme, wiki} or path in DEFAULT_IGNORES:
        return True
    return path.startswith(("docs/", "wiki/")) and path.lower().endswith((".md", ".mdx", ".txt"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check that README and Wiki changed with repository behavior changes."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root or child path")
    parser.add_argument("--base", default="HEAD", help="Base ref for working-tree diff")
    parser.add_argument("--readme", default="README.md", help="README path relative to repo root")
    parser.add_argument("--wiki", default="WIKI.md", help="Wiki path relative to repo root")
    args = parser.parse_args()

    repo_root = find_repo_root(Path(args.repo_root))
    readme = args.readme.replace("\\", "/")
    wiki = args.wiki.replace("\\", "/")
    files = changed_files(repo_root, args.base)

    if not files:
        print("No repository changes detected.")
        return 0

    behavior_files = sorted(path for path in files if not is_doc_only(path, readme, wiki))
    if not behavior_files:
        print("Only documentation/changelog changes detected; README/Wiki gate not required.")
        return 0

    missing = [path for path in (readme, wiki) if path not in files]
    if missing:
        print("README/Wiki freshness gate failed.", file=sys.stderr)
        print("Behavior-changing files:", file=sys.stderr)
        for path in behavior_files:
            print(f"  - {path}", file=sys.stderr)
        print("Missing documentation updates:", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
        return 1

    print("README/Wiki freshness gate passed.")
    print(f"Behavior-changing files: {len(behavior_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
