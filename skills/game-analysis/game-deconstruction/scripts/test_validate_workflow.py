#!/usr/bin/env python3
"""Unit tests for validate_workflow.py."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from validate_workflow import PHASE_IDS, validate


TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "templates" / "workflow-state.json"


class WorkflowValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(TEMPLATE.read_text(encoding="utf-8"))

    def test_template_is_valid_active_state(self) -> None:
        self.assertEqual(validate(self.data), [])

    def test_rejects_phase_skip_and_missing_evidence(self) -> None:
        self.data["phases"][1]["status"] = "passed"
        self.data["phases"][1]["gate"]["status"] = "passed"
        self.data["phases"][1]["artifacts"] = ["plan.json"]
        for check in self.data["phases"][1]["gate"]["checks"]:
            check["status"] = "passed"
            check["evidence"] = "evidence.md"
        self.data["phases"][1]["gate"]["checks"][0]["evidence"] = ""
        errors = validate(self.data)
        self.assertTrue(any("没有 evidence" in error for error in errors))
        self.assertTrue(any("更早阶段尚未结束" in error for error in errors))

    def test_rejects_completed_mode_with_required_phase_missing(self) -> None:
        self.data["status"] = "passed"
        self.data["current_phase"] = "P8"
        errors = validate(self.data)
        self.assertTrue(any("必需阶段" in error for error in errors))

    def test_passed_artifacts_can_be_checked_on_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scope.md").write_text("ok", encoding="utf-8")
            phase = self.data["phases"][0]
            phase["status"] = "passed"
            phase["artifacts"] = ["scope.md"]
            phase["gate"]["status"] = "passed"
            for check in phase["gate"]["checks"]:
                check["status"] = "passed"
                check["evidence"] = "scope.md"
            self.data["phases"][1]["status"] = "in_progress"
            self.data["current_phase"] = "P1"
            self.assertEqual(validate(self.data, root), [])

    def test_phase_order_is_fixed(self) -> None:
        swapped = copy.deepcopy(self.data)
        swapped["phases"][0], swapped["phases"][1] = swapped["phases"][1], swapped["phases"][0]
        errors = validate(swapped)
        self.assertTrue(any(", ".join(PHASE_IDS) in error for error in errors))


if __name__ == "__main__":
    unittest.main()
