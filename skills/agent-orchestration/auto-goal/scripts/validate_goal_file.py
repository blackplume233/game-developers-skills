#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED_SECTIONS = [
    "Goal",
    "Constraints",
    "Execution Guidance",
    "State",
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
    "execution_mode",
    "native_goal_id",
    "current_loop",
    "next_sub_goal",
    "last_verified_loop",
    "references",
]


def section_body(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^##\s+|\Z)",
        re.MULTILINE,
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def has_meaningful_content(body: str) -> bool:
    lines = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith("<!--") or line.endswith("-->"):
            continue
        if line in {"-", "- [ ]"}:
            continue
        lines.append(line)
    return bool(lines)


def extract_status(body: str) -> str:
    match = re.search(r"^\s*status\s*:\s*([A-Za-z_-]+)\s*$", body, re.MULTILINE)
    return match.group(1).strip().lower() if match else ""


def parse_yamlish_state(body: str) -> dict:
    body = re.sub(r"^```(?:yaml|yml)?\s*$", "", body, flags=re.MULTILINE)
    body = re.sub(r"^```\s*$", "", body, flags=re.MULTILINE)
    state = {}
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        state[key.strip()] = value.strip()
    return state


def validate(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    errors = []
    warnings = []

    if not re.search(r"^#\s+(Auto Goal Task|Goal)\s*$", text, re.MULTILINE):
        errors.append("missing top-level '# Auto Goal Task' or '# Goal' heading")

    for section in REQUIRED_SECTIONS:
        body = section_body(text, section)
        if not body:
            errors.append(f"missing section: {section}")
        elif section in {"Goal", "State"} and not has_meaningful_content(body):
            errors.append(f"section has no meaningful content: {section}")
        elif not has_meaningful_content(body):
            warnings.append(f"section appears empty: {section}")

    state = parse_yamlish_state(section_body(text, "State"))
    status = state.get("status", "").lower() or extract_status(section_body(text, "State"))
    if not status:
        errors.append("State section must include 'status: <value>'")
    elif status not in VALID_STATUSES:
        errors.append(
            "invalid status: "
            + status
            + " (expected one of "
            + ", ".join(sorted(VALID_STATUSES))
            + ")"
        )

    for key in REQUIRED_STATE_KEYS:
        if key not in state:
            errors.append(f"State section must include '{key}: <value>'")

    execution_mode = state.get("execution_mode", "")
    if execution_mode and execution_mode not in VALID_EXECUTION_MODES:
        errors.append(
            "invalid execution_mode: "
            + execution_mode
            + " (expected one of "
            + ", ".join(sorted(VALID_EXECUTION_MODES))
            + ")"
        )

    native_goal_id = state.get("native_goal_id", "")
    if execution_mode.startswith("native-") and native_goal_id in {"", "null", "none"}:
        errors.append("native execution_mode requires a non-null native_goal_id")

    return {
        "path": str(path),
        "valid": not errors,
        "status": status or None,
        "state": state,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a file-backed Goal markdown file.")
    parser.add_argument("goal_file", help="Path to goal.md")
    args = parser.parse_args()

    path = Path(args.goal_file)
    if not path.exists():
        print(json.dumps({"valid": False, "errors": [f"file not found: {path}"]}, ensure_ascii=False, indent=2))
        return 1

    result = validate(path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
