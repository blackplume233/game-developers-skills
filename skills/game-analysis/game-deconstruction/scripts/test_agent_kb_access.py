from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_kb_access import AgentKnowledgeBase, DATASETS


class AgentKnowledgeBaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        manifest = {
            "schema_version": "1.0", "game": "Test Game", "build": "42",
            "counts": {}, "release_boundary": {"internal_reviews": False},
        }
        (self.root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        records = {
            "concept": [{
                "id": "concept:rescue", "kind": "concept", "title": "Pawn 救援",
                "aliases": ["SavePartyMember"], "status": "confirmed",
                "plain_definition": "帮助倒下的队友", "evidence_paths": ["book/01.md"],
                "engineering_identity": {"static_config": "GoalAsset", "runtime_state": "GoalInstance"},
                "explanation_contract_version": "1.1",
                "decision_logic": {
                    "kind": "boolean_predicate", "canonical": "can_help AND needs_help",
                    "terms": [{"symbol": "can_help", "meaning": "救援者可行动"}],
                    "evaluation_order": ["检查救援者", "检查目标"], "short_circuit": "任一失败即不成立",
                },
                "runtime_sequence": [{
                    "step_id": "reserve", "order": 1, "trigger": "Goal 成立",
                    "inputs": ["目标"], "operation": "预留交互点",
                    "outputs": [{"value": "预留点", "consumer": "接近步骤", "effect": "作为移动目标"}],
                }],
                "tuning_contract": {"availability": "present", "items": [{
                    "control_locator": "Goal.Priority", "current_value": "3", "change": "提高",
                    "direct_effect": "候选权重提高", "downstream_effect": "更容易进入救援流程",
                    "tradeoff": "可能打断战斗职责",
                }]},
                "chain_position": {"upstream": ["情况判断"], "current": "救援 Goal", "downstream": ["救援动作"], "unknown_edges": []},
                "runtime_methods": ["evaluateSituation"],
            }],
            "claim": [{
                "id": "claim:rescue-goal", "kind": "claim", "statement": "目标资产引用救援判断",
                "concept_ids": ["concept:rescue"], "status": "confirmed",
                "evidence_paths": ["files/goal.md"],
            }],
            "asset": [{
                "id": "asset:goal", "kind": "asset", "asset_path": "natives/ai/goal.user.2",
                "name": "goal.user.2", "status": "confirmed", "concept_ids": ["concept:rescue"],
                "evidence_paths": ["files/goal.md"],
            }, {
                "id": "asset:action", "kind": "asset", "asset_path": "natives/ai/action.user.2",
                "name": "action.user.2", "status": "confirmed", "evidence_paths": ["files/action.md"],
            }],
            "relation": [{
                "id": "relation:1", "kind": "relation", "source_asset_id": "asset:goal",
                "target_asset_id": "asset:action", "source_asset_path": "natives/ai/goal.user.2",
                "target_asset_path": "natives/ai/action.user.2", "field_location": "DecisionPack",
                "status": "confirmed", "evidence_paths": ["files/goal.md"],
            }],
            "method": [{
                "id": "method:1", "kind": "method", "label": "evaluateSituation",
                "status": "confirmed", "evidence_paths": ["binary/methods.json"],
            }],
            "source": [{"id": "source:book", "kind": "source", "path": "book/01.md"}],
            "chunk": [{
                "id": "chunk:1", "kind": "chunk", "title": "救援案例", "text": "配置把判断接到行动。",
                "path": "book/01.md", "status": "confirmed", "evidence_paths": ["book/01.md"],
            }],
        }
        for kind, filename in DATASETS.items():
            content = "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records.get(kind, []))
            (self.root / filename).write_text(content, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_synonym_search_and_pagination(self) -> None:
        kb = AgentKnowledgeBase(self.root)
        result = kb.search("救人", kinds="concept", limit=1)
        self.assertEqual(result["results"][0]["id"], "concept:rescue")
        self.assertEqual(result["limit"], 1)
        self.assertIn("has_more", result)

    def test_context_groups_evidence(self) -> None:
        kb = AgentKnowledgeBase(self.root)
        result = kb.context("Pawn 救援", limit=8)
        self.assertEqual(result["build"], "42")
        self.assertTrue(any(item["id"] == "claim:rescue-goal" for item in result["claims"]))
        self.assertIn("files/goal.md", result["evidence_paths"])
        self.assertEqual(result["evidence_path_base"], "workspace_root")
        self.assertTrue(any(item["id"] == "method:1" for item in result["methods"]))
        concept = next(item for item in result["concepts"] if item["id"] == "concept:rescue")
        self.assertEqual(concept["explanation_contract_version"], "1.1")
        self.assertIn("decision_logic", concept)
        self.assertIn("runtime_sequence", concept)
        self.assertIn("tuning_contract", concept)

    def test_mechanism_questions_retrieve_executable_contract(self) -> None:
        kb = AgentKnowledgeBase(self.root)
        cases = {
            "Pawn 救援怎么做": "runtime_sequence",
            "Pawn 救援成立条件": "decision_logic",
            "Pawn 救援怎么调参": "tuning_contract",
        }
        for query, expected_term in cases.items():
            with self.subTest(query=query):
                result = kb.search(query, kinds="concept", limit=1)
                self.assertEqual(result["results"][0]["id"], "concept:rescue")
                self.assertIn(expected_term, result["expanded_terms"])
                self.assertIn(expected_term, result["results"][0])

    def test_long_question_uses_specific_domain_anchors(self) -> None:
        kb = AgentKnowledgeBase(self.root)
        result = kb.search("Pawn 救援以前做了哪些配置判断，最终动画能否下结论")
        self.assertTrue(result["results"])
        self.assertLessEqual(result["total_count"], 4)
        self.assertFalse(any(item["id"] == "asset:action" for item in result["results"]))

    def test_asset_neighbors_keep_both_paths(self) -> None:
        kb = AgentKnowledgeBase(self.root)
        result = kb.neighbors("natives/ai/goal.user.2")
        edge = result["results"][0]
        self.assertEqual(edge["source_asset_path"], "natives/ai/goal.user.2")
        self.assertEqual(edge["target_asset_path"], "natives/ai/action.user.2")

    def test_discovery_documents_are_machine_readable(self) -> None:
        kb = AgentKnowledgeBase(self.root)
        self.assertIn("/api/agent/context", kb.llms_text("http://127.0.0.1:1"))
        spec = kb.openapi()
        self.assertEqual(spec["openapi"], "3.1.0")
        self.assertIn("/api/agent/search", spec["paths"])

    def test_internal_material_is_rejected(self) -> None:
        with (self.root / "chunks.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"id": "chunk:leak", "kind": "chunk", "text": ".internal/reviews/secret"}) + "\n")
        with self.assertRaises(ValueError):
            AgentKnowledgeBase(self.root)


if __name__ == "__main__":
    unittest.main()
