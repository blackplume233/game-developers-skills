#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from goal_state import parse_state


SECTION_ALIASES = {
    "goal": ["目标", "Goal"],
    "constraints": ["约束", "Constraints"],
    "execution_guidance": ["执行指导", "Execution Guidance"],
    "state": ["状态", "State"],
}

VALID_TOP_LEVEL_HEADINGS = [
    "Auto Goal 任务",
    "Auto Goal Task",
    "Goal",
    "目标",
]

VALID_STATUSES = {
    "draft",
    "active",
    "paused",
    "blocked",
    "wrong-direction",
    "complete",
}

VALID_EXECUTION_MODES = {
    "native-codex-goal",
    "native-claude-goal",
    "simulated-file-goal",
}

REQUIRED_STATE_KEYS = [
    "updated_at",
    "artifact_language",
    "execution_mode",
    "native_goal_id",
    "current_loop",
    "next_sub_goal",
    "last_verified_loop",
    "references",
]


def heading_pattern(heading: str) -> str:
    return re.escape(heading).replace(r"\ ", r"\s+")


def section_body(text: str, section_key: str) -> str:
    aliases = SECTION_ALIASES[section_key]
    heading_alternatives = "|".join(heading_pattern(alias) for alias in aliases)
    pattern = re.compile(
        rf"^##\s+(?:{heading_alternatives})\s*$([\s\S]*?)(?=^##\s+|\Z)",
        re.MULTILINE,
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def has_meaningful_content(body: str) -> bool:
    lines = []
    in_comment = False
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("<!--"):
            in_comment = not line.endswith("-->")
            continue
        if in_comment:
            if line.endswith("-->"):
                in_comment = False
            continue
        if line in {"-", "- [ ]"}:
            continue
        lines.append(line)
    return bool(lines)


def extract_status(body: str) -> str:
    match = re.search(r"^\s*status\s*:\s*([A-Za-z_-]+)\s*$", body, re.MULTILINE)
    return match.group(1).strip().lower() if match else ""


def has_valid_top_heading(text: str) -> bool:
    alternatives = "|".join(heading_pattern(heading) for heading in VALID_TOP_LEVEL_HEADINGS)
    return bool(re.search(rf"^#\s+(?:{alternatives})\s*$", text, re.MULTILINE))


def validate(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    errors = []
    warnings = []

    if not has_valid_top_heading(text):
        errors.append("缺少顶层标题：需要 '# Auto Goal 任务'、'# Auto Goal Task'、'# Goal' 或 '# 目标'")

    for section_key, aliases in SECTION_ALIASES.items():
        body = section_body(text, section_key)
        label = " / ".join(aliases)
        if not body:
            errors.append(f"缺少章节：{label}")
        elif section_key in {"goal", "state"} and not has_meaningful_content(body):
            errors.append(f"章节没有有效内容：{label}")
        elif not has_meaningful_content(body):
            warnings.append(f"章节看起来为空：{label}")

    state = parse_state(text)
    status = state.get("status", "").lower() or extract_status(section_body(text, "state"))
    if not status:
        errors.append("状态章节必须包含 'status: <value>'")
    elif status not in VALID_STATUSES:
        errors.append(
            "无效 status: "
            + status
            + "（期望值之一："
            + ", ".join(sorted(VALID_STATUSES))
            + "）"
        )

    for key in REQUIRED_STATE_KEYS:
        if key not in state:
            errors.append(f"状态章节必须包含 '{key}: <value>'")

    artifact_language = state.get("artifact_language", "")
    if artifact_language.lower() in {"", "null", "none"}:
        errors.append("artifact_language 必须声明持久文档语言，例如 zh-CN、en-US 或 bilingual-zh-en")

    execution_mode = state.get("execution_mode", "")
    if execution_mode and execution_mode not in VALID_EXECUTION_MODES:
        errors.append(
            "无效 execution_mode: "
            + execution_mode
            + "（期望值之一："
            + ", ".join(sorted(VALID_EXECUTION_MODES))
            + "）"
        )

    native_goal_id = state.get("native_goal_id", "")
    if execution_mode.startswith("native-") and native_goal_id in {"", "null", "none"}:
        errors.append("native execution_mode 需要非空 native_goal_id")

    return {
        "path": str(path),
        "valid": not errors,
        "status": status or None,
        "state": state,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="校验文件化 Auto Goal Markdown。")
    parser.add_argument("goal_file", help="goal.md 路径")
    args = parser.parse_args()

    path = Path(args.goal_file)
    if not path.exists():
        print(json.dumps({"valid": False, "errors": [f"文件不存在：{path}"]}, ensure_ascii=False, indent=2))
        return 1

    result = validate(path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
