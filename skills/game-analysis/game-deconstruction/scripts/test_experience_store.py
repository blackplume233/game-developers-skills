from __future__ import annotations

import argparse
import importlib.util
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("experience_store.py")
SPEC = importlib.util.spec_from_file_location("experience_store", MODULE_PATH)
assert SPEC and SPEC.loader
store = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(store)


def experience(
    game: str = "Game A",
    source_group: str = "source-a",
    pattern_key: str = "ai.perception.test-pattern",
    rule: str = "在相同条件下重复出现的可证伪跨游戏规则。",
    outcome: str = "supported",
    confidence: float = 0.9,
    evidence_level: str = "E1",
) -> dict:
    return {
        "learning_context": {
            "identity": "game-designer",
            "learning_goal": "学习敌人 AI 如何服务战斗节奏与玩家读招体验。",
            "design_questions": ["该机制解决了什么战斗体验问题？"],
            "authorized_materials": ["runtime-observation", "public-source"],
            "output_use": "learning-and-prototyping",
        },
        "authorization_scope": "runtime-observation",
        "game": {"name": game, "version": "1.0", "platform": "PC", "engine": "unknown"},
        "summary": "这是一条用于验证经验学习流程的完整拆解结论。",
        "domains": ["ai"],
        "evidence_level": evidence_level,
        "confidence": confidence,
        "outcome": outcome,
        "network_safe": True,
        "source_group": source_group,
        "source_artifact_type": "reader-learning-report",
        "source_report": "docs/final-learning-report.md",
        "lessons": [
            {
                "pattern_key": pattern_key,
                "rule": rule,
                "scope": "动作游戏敌人 AI",
                "outcome": outcome,
                "confidence": confidence,
            }
        ],
        "designer_takeaways": ["把技术发现转化为可配置的敌人读招与反应窗口规则。"],
    }


def promotion_args(**overrides) -> argparse.Namespace:
    values = {
        "min_support": 5,
        "min_games": 3,
        "min_confidence": 0.8,
        "consensus_ratio": 0.8,
        "dry_run": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class NormalizeAndQueueTests(unittest.TestCase):
    def test_transport_flag_does_not_change_identity(self) -> None:
        first = experience()
        second = experience()
        second["network_safe"] = False
        self.assertEqual(store.normalize_record(first)["fingerprint"], store.normalize_record(second)["fingerprint"])

    def test_queue_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_path = root / "input.json"
            input_path.write_text(json.dumps(experience(), ensure_ascii=False), encoding="utf-8")
            _, target, created = store.queue_record(input_path, root / "queue")
            _, second_target, created_again = store.queue_record(input_path, root / "queue")
            self.assertTrue(created)
            self.assertFalse(created_again)
            self.assertEqual(target, second_target)

    def test_invalid_or_unscoped_record_is_rejected(self) -> None:
        value = experience()
        value["domains"] = ["unknown-domain"]
        with self.assertRaises(store.ExperienceError):
            store.normalize_record(value)

    def test_non_designer_learning_context_is_rejected(self) -> None:
        value = experience()
        value["learning_context"]["identity"] = "asset-extractor"
        with self.assertRaises(store.ExperienceError):
            store.normalize_record(value)

    def test_sensitive_token_and_local_user_path_are_rejected_for_upload(self) -> None:
        token_record = store.normalize_record(experience())
        token_record["observations"] = ["token=secret_abcdefghijklmnopqrstuvwxyz"]
        with self.assertRaises(store.ExperienceError):
            store.assert_upload_safe(token_record)
        path_record = store.normalize_record(experience())
        path_record["source_report"] = r"C:\Users\developer\private-report.md"
        with self.assertRaises(store.ExperienceError):
            store.assert_upload_safe(path_record)

    def test_public_url_is_allowed_by_upload_scan(self) -> None:
        value = store.normalize_record(experience())
        value["source_report"] = "https://example.com/public-analysis"
        store.assert_upload_safe(value)

    def test_internal_review_path_is_rejected(self) -> None:
        value = experience()
        value["source_report"] = ".internal/reviews/feynman-subagent-review.md"
        with self.assertRaises(store.ExperienceError):
            store.normalize_record(value)

    def test_internal_review_marker_is_rejected(self) -> None:
        value = experience()
        value["summary"] = "这是一条误把独立费曼审查内容作为游戏知识来源的经验记录。"
        with self.assertRaises(store.ExperienceError):
            store.normalize_record(value)

    def test_internal_review_artifact_type_is_rejected(self) -> None:
        value = experience()
        value["source_artifact_type"] = "internal-review"
        with self.assertRaises(store.ExperienceError):
            store.normalize_record(value)


class PromotionTests(unittest.TestCase):
    def normalized_records(self, count: int = 5, evidence_level: str = "E1") -> list[dict]:
        games = ["Game A", "Game B", "Game C", "Game A", "Game B", "Game C"]
        return [
            store.normalize_record(experience(games[index], f"source-{index}", evidence_level=evidence_level))
            for index in range(count)
        ]

    def test_threshold_n_minus_one_n_and_n_plus_one(self) -> None:
        args = promotion_args()
        self.assertEqual(store.pattern_candidates(self.normalized_records(4), 5, 3, 0.8, 0.8), [])
        self.assertEqual(len(store.pattern_candidates(self.normalized_records(5), 5, 3, 0.8, 0.8)), 1)
        self.assertEqual(len(store.pattern_candidates(self.normalized_records(6), 5, 3, 0.8, 0.8)), 1)

    def test_same_game_and_source_group_counts_once(self) -> None:
        records = [store.normalize_record(experience("Game A", "same-source")) for _ in range(6)]
        self.assertEqual(store.pattern_candidates(records, 5, 3, 0.8, 0.8), [])

    def test_low_grade_evidence_cannot_promote(self) -> None:
        self.assertEqual(store.pattern_candidates(self.normalized_records(6, "E4"), 5, 3, 0.8, 0.8), [])

    def test_conflict_revokes_existing_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            env = {
                "GAME_DECONSTRUCTION_LEARNED_ROOT": str(root / "learned"),
                "GAME_DECONSTRUCTION_LOCAL_ROOT": str(root / "local"),
            }
            with mock.patch.dict(os.environ, env, clear=False):
                first = store.promote_patterns(self.normalized_records(5), promotion_args())
                self.assertEqual(first["changed_patterns"], ["ai.perception.test-pattern"])
                conflict = store.normalize_record(
                    experience("Game D", "source-conflict", outcome="refuted", confidence=0.95)
                )
                second = store.promote_patterns(self.normalized_records(5) + [conflict], promotion_args())
                self.assertEqual(second["changed_patterns"], ["-ai.perception.test-pattern"])
                learned = store.load_json(root / "learned" / "learned-patterns.json")
                self.assertEqual(learned["patterns"], [])


class RemoteIntegrityTests(unittest.TestCase):
    def test_remote_payload_tampering_is_detected(self) -> None:
        record = store.normalize_record(experience())
        payload = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        page = {
            "id": "page-id",
            "properties": {
                "Fingerprint": {"rich_text": [{"plain_text": "wrong"}]},
                "Record ID": {"rich_text": [{"plain_text": record["record_id"]}]},
            },
        }
        response = {
            "results": [
                {"type": "code", "code": {"rich_text": [{"plain_text": payload}]}}
            ]
        }
        with mock.patch.object(store, "notion_request", return_value=response):
            with self.assertRaises(store.ExperienceError):
                store.retrieve_record(page)

    def test_non_idempotent_page_create_is_not_blindly_retried(self) -> None:
        with mock.patch.dict(os.environ, {"NOTION_TOKEN": "test-token"}, clear=False):
            with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")) as urlopen:
                with self.assertRaises(store.ExperienceError):
                    store.notion_request("POST", "/pages", {"test": True})
                self.assertEqual(urlopen.call_count, 1)

    def test_schema_drift_fails_closed(self) -> None:
        source = {
            "properties": {
                "Name": {"type": "title"},
                "Record ID": {"type": "number"}
            }
        }
        with mock.patch.object(store, "notion_request", return_value=source):
            with self.assertRaises(store.ExperienceError):
                store.validate_data_source("source-id")

    def test_missing_token_is_reported_before_missing_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = {
                "GAME_DECONSTRUCTION_LOCAL_ROOT": temp,
                "NOTION_TOKEN": "",
                "NOTION_PARENT_PAGE_ID": "",
                "NOTION_GAME_DECONSTRUCTION_DATA_SOURCE_ID": "",
                "NOTION_GAME_DECONSTRUCTION_DATABASE_ID": "",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                with self.assertRaisesRegex(store.ExperienceError, "NOTION_TOKEN"):
                    store.get_data_source_id(auto_create=True)


if __name__ == "__main__":
    unittest.main()
