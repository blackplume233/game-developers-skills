#!/usr/bin/env python3
"""Validate the structure of a character-specific knowledge-comic skill.

This is a package-contract check. It does not replace semantic visual review,
privacy auditing, source verification, or rights review.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_FILES = (
    "SKILL.md",
    "references/character-bible.md",
    "references/voice-and-catchphrases.md",
    "references/spirit-and-rendering.md",
    "references/quality-checklist.md",
    "references/sources.md",
    "assets/templates/brief.yaml",
    "scripts/validate_skill.py",
)

CHARACTER_BIBLE_CONCEPTS = {
    "evidence status": ("Evidence Status", "身份信息", "参考图输入", "证据状态"),
    "identity anchors": ("Identity Anchors", "Character Lock", "身份锚点"),
    "expression policy": ("Expression Policy", "表情策略", "固定脸谱", "神韵锁定"),
    "anatomy lock": ("Anatomy Lock", "肢体拓扑", "动作库", "圆手"),
    "render lock": ("Render Lock", "渲染锁", "渲染锁定"),
    "unknowns": ("Unknowns", "未知项", "标为未知"),
    "negative constraints": ("Negative Constraints", "禁止漂移", "负面约束"),
}

SKILL_CONCEPTS = {
    "character lock": ("Character Lock",),
    "expression policy": ("Expression Policy", "表情策略", "固定脸谱"),
    "anatomy lock": ("Anatomy Lock", "肢体拓扑", "圆手硬约束"),
    "render lock": ("Render Lock", "渲染锁", "渲染"),
    "stop condition": ("停止条件", "停止后", "提前停止"),
    "output contract": ("输出契约",),
}

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line or line.startswith((" ", "\t")):
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip("'\"")
    return result


def validate(root: Path, allow_image_assets: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.is_file():
            errors.append(f"missing: {relative}")
        elif path.stat().st_size == 0:
            errors.append(f"empty: {relative}")

    skill_path = root / "SKILL.md"
    if skill_path.is_file():
        text = skill_path.read_text(encoding="utf-8")
        metadata = parse_frontmatter(text)
        for field in ("name", "version", "description"):
            if not metadata.get(field):
                errors.append(f"SKILL.md: missing frontmatter field {field}")
        if metadata.get("name") and metadata["name"] != root.name:
            errors.append(
                f"SKILL.md: name {metadata['name']!r} does not match folder {root.name!r}"
            )
        version = metadata.get("version", "")
        if version and not re.fullmatch(r"\d+\.\d+\.\d+", version):
            errors.append(f"SKILL.md: invalid semantic version {version!r}")
        for concept, aliases in SKILL_CONCEPTS.items():
            if not any(alias in text for alias in aliases):
                errors.append(
                    f"SKILL.md: missing {concept}; expected one of {aliases!r}"
                )
        if not any(term in text for term in ("不分发", "不进入 Skill", "不复制进")):
            errors.append("SKILL.md: missing reference-image non-distribution boundary")

    bible_path = root / "references/character-bible.md"
    if bible_path.is_file():
        bible = bible_path.read_text(encoding="utf-8")
        for concept, aliases in CHARACTER_BIBLE_CONCEPTS.items():
            if not any(alias in bible for alias in aliases):
                errors.append(
                    f"character-bible.md: missing {concept}; expected one of {aliases!r}"
                )

    if not allow_image_assets:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                errors.append(
                    f"reference/generated image packaged by default: {path.relative_to(root)}"
                )

    absolute_path_patterns = (
        re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+", re.IGNORECASE),
        re.compile(r"/(?:home|Users)/[^/\s]+"),
    )
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() in IMAGE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            warnings.append(f"non-UTF-8 file not privacy-scanned: {path.relative_to(root)}")
            continue
        if any(pattern.search(text) for pattern in absolute_path_patterns):
            warnings.append(f"possible user-specific absolute path: {path.relative_to(root)}")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir", type=Path)
    parser.add_argument(
        "--allow-image-assets",
        action="store_true",
        help="Allow image assets only after an explicit rights/distribution review.",
    )
    args = parser.parse_args()
    root = args.skill_dir.resolve()
    if not root.is_dir():
        print(f"FAIL\n- not a directory: {root}")
        return 1

    errors, warnings = validate(root, args.allow_image_assets)
    print("PASS" if not errors else "FAIL")
    print(f"skill: {root}")
    print(f"files reviewed: {sum(1 for path in root.rglob('*') if path.is_file())}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    print(
        "note: structural validation does not replace visual, privacy, source, or rights review"
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
