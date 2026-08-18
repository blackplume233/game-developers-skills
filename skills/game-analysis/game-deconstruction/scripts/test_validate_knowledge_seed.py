#!/usr/bin/env python3
"""Unit tests for validate_knowledge_seed.py."""

from __future__ import annotations

import copy
import unittest

from validate_knowledge_seed import validate


def valid_seed() -> dict:
    evidence = ["docs/mechanism.md"]
    return {
        "schema_version": "1.0",
        "concepts": [{
            "id": "concept:example", "name": "示例机制", "summary": "示例摘要",
            "plain_definition": "用普通语言解释机制角色。", "config_shape": "Definition → Rules",
            "explanation_contract_version": "1.1", "status": "confirmed", "confidence": "high",
            "evidence_paths": evidence,
            "decision_logic": {
                "kind": "boolean_predicate", "canonical": "A AND NOT B",
                "terms": [{"symbol": "A", "meaning": "正向条件", "source_locator": "Definition.Required",
                           "status": "confirmed", "evidence_paths": evidence}],
                "evaluation_order": ["先检查排除项", "再检查正向项"],
                "short_circuit": "排除项命中立即失败", "limitations": [], "next_probe": "",
            },
            "runtime_sequence": [{
                "step_id": "check", "order": 1, "trigger": "规则重评估", "inputs": ["运行时事实"],
                "operation": "计算谓词", "outputs": [{"value": "资格结果", "consumer": "选择器", "effect": "更新候选",
                                                     "consumer_status": "confirmed", "next_probe": ""}],
                "status": "confirmed", "evidence_paths": evidence, "next_probe": "",
            }],
            "tuning_contract": {
                "availability": "present", "reason": "", "limitations": [], "next_probe": "",
                "items": [{"control_locator": "Definition.Required", "current_value": "A", "change": "替换引用",
                           "value_status": "confirmed", "control_stage": "eligibility",
                           "direct_effect": "改变入口资格", "downstream_effect": "改变候选集合",
                           "tradeoff": "条件过严会减少触发", "effect_status": "confirmed",
                           "status": "confirmed", "evidence_paths": evidence,
                           "next_probe": ""}],
            },
            "chain_position": {"upstream": ["事实"], "current": "资格", "downstream": ["候选"],
                               "unknown_edges": [{"from": "选择器", "to": "表现", "missing_proof": "缺少调用边",
                                                  "impact": "不能确认最终表现", "next_probe": "追踪消费者",
                                                  "status": "unknown"}]},
        }],
        "claims": [{"id": "claim:example", "statement": "示例机制使用排除优先的入口谓词。",
                    "status": "confirmed", "confidence": "high", "concept_ids": ["concept:example"],
                    "evidence_paths": evidence}],
    }


class KnowledgeSeedValidationTests(unittest.TestCase):
    def test_valid_seed_passes(self) -> None:
        self.assertEqual(validate(valid_seed()), [])

    def test_template_placeholder_is_rejected(self) -> None:
        data = valid_seed()
        data["concepts"][0]["name"] = "[概念名称]"
        self.assertTrue(any("占位符" in error for error in validate(data)))

    def test_confirmed_term_requires_evidence(self) -> None:
        data = valid_seed()
        data["concepts"][0]["decision_logic"]["terms"][0]["evidence_paths"] = []
        self.assertTrue(any("evidence_paths" in error for error in validate(data)))

    def test_runtime_order_must_be_contiguous(self) -> None:
        data = valid_seed()
        data["concepts"][0]["runtime_sequence"][0]["order"] = 2
        self.assertTrue(any("连续递增" in error for error in validate(data)))

    def test_unknown_edge_must_be_structured(self) -> None:
        data = valid_seed()
        data["concepts"][0]["chain_position"]["unknown_edges"] = ["missing adapter"]
        self.assertTrue(any("结构化对象" in error for error in validate(data)))

    def test_internal_or_absolute_evidence_is_rejected(self) -> None:
        for path in ("C:\\private\\evidence.md", ".internal/reviews/verdict.md"):
            with self.subTest(path=path):
                data = valid_seed()
                data["concepts"][0]["evidence_paths"] = [path]
                self.assertTrue(validate(data))

    def test_unknown_tuning_requires_probe(self) -> None:
        data = valid_seed()
        data["concepts"][0]["tuning_contract"] = {
            "availability": "unknown", "items": [], "reason": "", "limitations": [], "next_probe": ""
        }
        self.assertTrue(any("next_probe" in error for error in validate(data)))

    def test_confirmed_value_can_keep_unknown_effect(self) -> None:
        data = valid_seed()
        item = data["concepts"][0]["tuning_contract"]["items"][0]
        item.update({"value_status": "confirmed", "effect_status": "unknown", "control_stage": "unknown", "next_probe": "追踪字段消费者"})
        item["status"] = "unknown"
        self.assertEqual(validate(data), [])

    def test_unknown_consumer_requires_probe_and_unknown_edge(self) -> None:
        data = valid_seed()
        output = data["concepts"][0]["runtime_sequence"][0]["outputs"][0]
        output.update({"consumer": "unknown", "consumer_status": "unknown", "next_probe": "追踪输出读取者"})
        data["concepts"][0]["chain_position"]["unknown_edges"] = []
        self.assertTrue(any("消费者未知" in error for error in validate(data)))


if __name__ == "__main__":
    unittest.main()
