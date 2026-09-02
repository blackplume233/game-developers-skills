#!/usr/bin/env python3
"""Validate the character-skill-forge package."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REQUIRED_FILES = (
    "SKILL.md",
    "references/workflow.md",
    "references/target-skill-contract.md",
    "references/evaluation-rubric.md",
    "assets/templates/character-study.yaml",
    "scripts/validate_character_skill.py",
)

REQUIRED_TERMS = (
    "Expression Policy",
    "Anatomy Lock",
    "Render Lock",
    "fixed | bounded | expressive",
    "最多 4 轮",
    "连续两轮",
    "不代表训练、微调",
    "不得声称角色相似度通过",
    "不等于获准安装、提交或发布",
)


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
        for term in REQUIRED_TERMS:
            if term not in text:
                errors.append(f"SKILL.md: missing required term {term!r}")

    target_validator = root / "scripts/validate_character_skill.py"
    if target_validator.is_file():
        source = target_validator.read_text(encoding="utf-8")
        try:
            compile(source, str(target_validator), "exec")
        except SyntaxError as exc:
            errors.append(f"validate_character_skill.py: {exc}")

    print("PASS" if not errors else "FAIL")
    print(f"skill: {root}")
    print(f"required files: {len(REQUIRED_FILES)}")
    for error in errors:
        print(f"- {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

