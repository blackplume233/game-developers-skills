#!/usr/bin/env python3
"""Validate a phase-gated game-deconstruction workflow state file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PHASE_IDS = [f"P{i}" for i in range(9)]
PHASE_STATUS = {"pending", "in_progress", "passed", "blocked", "skipped"}
GATE_STATUS = {"pending", "passed", "failed", "blocked"}
CHECK_STATUS = {"pending", "passed", "failed", "blocked"}
REQUIRED_BY_MODE = {
    "recon": {"P0", "P1", "P2", "P3"},
    "deep-dive": {"P0", "P1", "P2", "P3", "P4", "P6"},
    "complete": {"P0", "P1", "P2", "P3", "P4", "P6", "P7", "P8"},
}


def add_error(errors: list[str], message: str) -> None:
    if message not in errors:
        errors.append(message)


def validate(data: dict[str, Any], project_root: Path | None = None) -> list[str]:
    errors: list[str] = []
    mode = data.get("mode")
    if mode not in REQUIRED_BY_MODE:
        add_error(errors, "mode 必须是 recon、deep-dive 或 complete")
    if data.get("status") not in {"active", "passed", "blocked"}:
        add_error(errors, "顶层 status 必须是 active、passed 或 blocked")

    phases = data.get("phases")
    if not isinstance(phases, list):
        return errors + ["phases 必须是数组"]
    ids = [phase.get("id") for phase in phases if isinstance(phase, dict)]
    if ids != PHASE_IDS:
        add_error(errors, f"phases 必须按顺序完整包含 {', '.join(PHASE_IDS)}")
        return errors

    in_progress: list[str] = []
    passed_boundary_open = True
    for phase in phases:
        phase_id = phase["id"]
        status = phase.get("status")
        if status not in PHASE_STATUS:
            add_error(errors, f"{phase_id}.status 非法")
            continue
        if status == "in_progress":
            in_progress.append(phase_id)

        gate = phase.get("gate")
        if not isinstance(gate, dict) or gate.get("status") not in GATE_STATUS:
            add_error(errors, f"{phase_id}.gate 缺失或状态非法")
            continue
        checks = gate.get("checks")
        if not isinstance(checks, list) or not checks:
            add_error(errors, f"{phase_id}.gate.checks 必须是非空数组")
            continue

        for check in checks:
            if not isinstance(check, dict) or check.get("status") not in CHECK_STATUS:
                add_error(errors, f"{phase_id} 存在非法 Gate check")
                continue
            if check.get("status") == "passed" and not str(check.get("evidence", "")).strip():
                add_error(errors, f"{phase_id}.{check.get('id', 'check')} 通过但没有 evidence")

        if status == "passed":
            if gate.get("status") != "passed":
                add_error(errors, f"{phase_id} 标为 passed，但 Gate 未通过")
            if any(check.get("status") != "passed" for check in checks if isinstance(check, dict)):
                add_error(errors, f"{phase_id} 标为 passed，但仍有 Gate check 未通过")
            artifacts = phase.get("artifacts")
            if not isinstance(artifacts, list) or not artifacts:
                add_error(errors, f"{phase_id} 标为 passed，但没有 artifacts")
            elif project_root:
                for artifact in artifacts:
                    if not isinstance(artifact, str) or not artifact.strip():
                        add_error(errors, f"{phase_id} 包含空 artifact")
                        continue
                    if artifact.startswith("["):
                        add_error(errors, f"{phase_id} artifact 仍是占位符: {artifact}")
                        continue
                    if not (project_root / artifact).exists():
                        add_error(errors, f"{phase_id} artifact 不存在: {artifact}")

        if status == "blocked" and not phase.get("blockers"):
            add_error(errors, f"{phase_id} 标为 blocked，但没有 blockers")
        if status == "skipped" and not str(phase.get("skip_reason", "")).strip():
            add_error(errors, f"{phase_id} 标为 skipped，但没有 skip_reason")

        if status in {"pending", "in_progress", "blocked"}:
            passed_boundary_open = False
        elif status == "passed" and not passed_boundary_open:
            add_error(errors, f"{phase_id} 已通过，但更早阶段尚未结束")

    if len(in_progress) > 1:
        add_error(errors, "同时只能有一个 in_progress 阶段")
    current = data.get("current_phase")
    if current not in PHASE_IDS:
        add_error(errors, "current_phase 非法")
    elif in_progress and current != in_progress[0]:
        add_error(errors, "current_phase 必须指向唯一的 in_progress 阶段")

    top_status = data.get("status")
    if mode in REQUIRED_BY_MODE and top_status == "passed":
        by_id = {phase["id"]: phase for phase in phases}
        for phase_id in REQUIRED_BY_MODE[mode]:
            if by_id[phase_id].get("status") != "passed":
                add_error(errors, f"顶层已 passed，但模式 {mode} 的必需阶段 {phase_id} 未通过")
    if top_status == "blocked" and not any(phase.get("status") == "blocked" for phase in phases):
        add_error(errors, "顶层 blocked，但没有 blocked 阶段")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", type=Path)
    parser.add_argument("--project-root", type=Path)
    args = parser.parse_args()
    data = json.loads(args.state.read_text(encoding="utf-8"))
    errors = validate(data, args.project_root.resolve() if args.project_root else None)
    result = {
        "status": "failed" if errors else "passed",
        "state": str(args.state.resolve()),
        "mode": data.get("mode"),
        "current_phase": data.get("current_phase"),
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
