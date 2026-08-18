from __future__ import annotations

import unittest

from validate_agent_knowledge_base import validate_mechanism_contract


class MechanismContractValidationTests(unittest.TestCase):
    def valid_concept(self) -> dict:
        return {
            "explanation_contract_version": "1.1",
            "decision_logic": {
                "kind": "boolean_predicate",
                "canonical": "ready AND target_needs_help",
                "evaluation_order": ["ready", "target_needs_help"],
            },
            "runtime_sequence": [{
                "order": 1,
                "outputs": [{"value": "target", "consumer": "action selector", "effect": "select action"}],
            }],
            "tuning_contract": {"availability": "none", "items": [], "reason": "没有可证实参数"},
            "chain_position": {"unknown_edges": []},
        }

    def test_valid_v11_contract(self) -> None:
        errors: list[str] = []
        validate_mechanism_contract(self.valid_concept(), "concepts.jsonl:1", errors)
        self.assertEqual(errors, [])

    def test_legacy_concept_remains_compatible(self) -> None:
        errors: list[str] = []
        validate_mechanism_contract({}, "concepts.jsonl:1", errors)
        self.assertEqual(errors, [])

    def test_missing_consumer_and_free_string_unknown_edge_fail(self) -> None:
        concept = self.valid_concept()
        concept["runtime_sequence"][0]["outputs"][0].pop("consumer")
        concept["chain_position"]["unknown_edges"] = ["animation edge"]
        errors: list[str] = []
        validate_mechanism_contract(concept, "concepts.jsonl:1", errors)
        self.assertTrue(any("without consumer" in item for item in errors))
        self.assertTrue(any("structured edge" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
