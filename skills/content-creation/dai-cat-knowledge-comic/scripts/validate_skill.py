#!/usr/bin/env python3
"""Validate the dai-cat-knowledge-comic skill package."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REQUIRED_FILES = [
    "SKILL.md",
    "references/character-bible.md",
    "references/voice-and-catchphrases.md",
    "references/quality-checklist.md",
    "references/sources.md",
    "assets/templates/brief.yaml",
]

REFERENCE_NOTICE = "仓库不分发游戏截图"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []

    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.is_file():
            errors.append(f"missing: {relative}")
        elif path.stat().st_size == 0:
            errors.append(f"empty: {relative}")

    skill_path = root / "SKILL.md"
    if skill_path.is_file():
        text = skill_path.read_text(encoding="utf-8")
        frontmatter = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        if not frontmatter:
            errors.append("SKILL.md: invalid or missing YAML frontmatter")
        else:
            metadata = frontmatter.group(1)
            for field in ("name", "version", "description"):
                if not re.search(rf"^{field}:\s*\S", metadata, re.MULTILINE):
                    errors.append(f"SKILL.md: missing frontmatter field {field}")

        required_terms = ["Gemini", "老大", "喵", "小苗", "同人创作", REFERENCE_NOTICE]
        for term in required_terms:
            if term not in text:
                errors.append(f"SKILL.md: missing required policy term {term}")

    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS")
    print(f"skill: {root}")
    print(f"required files: {len(REQUIRED_FILES)}")
    print("reference images: supplied per task (not distributed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
