#!/usr/bin/env python3
"""生成或校验技能仓库根目录的 skills.sh.json。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
CATEGORY_META = {
    "agent-orchestration": ("Agent Orchestration", "Agent 编排、委派与自主执行技能。"),
    "design": ("Design", "UI、UX 与应用设计技能。"),
    "dev-workflow": ("Development Workflow", "工程质量、调试、测试与交付工作流。"),
    "divination": ("Divination", "传统文化与决策辅助技能。"),
    "framework": ("Frameworks", "桌面端与跨平台框架开发技能。"),
    "gas-extension": ("Game Development", "游戏开发项目与扩展交付技能。"),
    "skill-management": ("Skill Management", "Skill 发现、维护、发布与仓库管理技能。"),
}


def repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "skills").is_dir() and (candidate / ".git").exists():
            return candidate
    raise ValueError(f"找不到技能仓库根目录: {start}")


def skill_name(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"缺少 YAML frontmatter: {path}")
    name_match = re.search(r"(?m)^name:\s*['\"]?([^\r\n'\"]+)", match.group(1))
    if not name_match or not name_match.group(1).strip():
        raise ValueError(f"frontmatter 缺少 name: {path}")
    return name_match.group(1).strip()


def fallback_meta(category: str) -> tuple[str, str]:
    title = " ".join(word.capitalize() for word in category.split("-"))
    return title, f"{title} 类技能。"


def build_config(root: Path) -> dict[str, object]:
    grouped: dict[str, list[str]] = {}
    seen: dict[str, Path] = {}
    for path in sorted((root / "skills").glob("*/*/SKILL.md")):
        category = path.relative_to(root / "skills").parts[0]
        name = skill_name(path)
        key = name.casefold().replace("_", "-").replace(" ", "-")
        if key in seen:
            raise ValueError(f"技能名重复: {name} ({seen[key]} 与 {path})")
        seen[key] = path
        grouped.setdefault(category, []).append(name)
    if not grouped:
        raise ValueError("skills/<category>/<skill>/SKILL.md 下未发现技能")

    groups = []
    for category in sorted(grouped):
        title, description = CATEGORY_META.get(category, fallback_meta(category))
        groups.append({
            "title": title,
            "description": description,
            "skills": sorted(grouped[category], key=str.casefold),
        })
    return {
        "$schema": "https://skills.sh/schemas/skills.sh.schema.json",
        "notGrouped": "bottom",
        "groupings": groups,
    }


def rendered(config: dict[str, object]) -> str:
    return json.dumps(config, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="生成或校验 skills.sh.json")
    parser.add_argument("--repo-root", default=".", help="技能仓库根目录或其子目录")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="写入根目录 skills.sh.json")
    mode.add_argument("--check", action="store_true", help="检查现有配置是否与技能清单一致")
    args = parser.parse_args()

    try:
        root = repo_root(Path(args.repo_root))
        expected = rendered(build_config(root))
        target = root / "skills.sh.json"
        if args.write:
            target.write_text(expected, encoding="utf-8", newline="\n")
            print(f"已生成 {target.relative_to(root)}")
            return 0
        if not target.exists():
            print("缺少 skills.sh.json；请运行 --write 生成。", file=sys.stderr)
            return 1
        actual = target.read_text(encoding="utf-8")
        if actual != expected:
            print("skills.sh.json 与当前技能清单不一致；请运行 --write 更新。", file=sys.stderr)
            return 1
        count = sum(len(group["skills"]) for group in build_config(root)["groupings"])
        print(f"skills.sh.json 校验通过：{count} 个技能。")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
