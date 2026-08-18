#!/usr/bin/env python3
"""Validate the curated knowledge seed and its mechanism explanation contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


STATUSES = {"confirmed", "inferred", "unknown", "self_build"}
CONFIDENCES = {"high", "medium", "low", "not_applicable"}
LOGIC_KINDS = {
    "boolean_predicate", "numeric_formula", "state_transition", "ordering",
    "mapping", "passthrough", "unknown", "not_applicable",
}
TUNING_AVAILABILITY = {"present", "none", "unknown"}
CONTROL_STAGES = {"enablement", "eligibility", "selection", "scheduling", "execution", "presentation", "unknown"}
WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")


def add_error(errors: list[str], location: str, message: str) -> None:
    errors.append(f"{location}: {message}")


def is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_placeholder(value: Any) -> bool:
    if not is_text(value):
        return False
    text = value.strip()
    return text.startswith("[") and text.endswith("]")


def validate_text(value: Any, location: str, errors: list[str], *, allow_empty: bool = False) -> None:
    if allow_empty and value == "":
        return
    if not is_text(value):
        add_error(errors, location, "必须是非空字符串")
    elif is_placeholder(value):
        add_error(errors, location, "仍是模板占位符")


def validate_evidence_paths(value: Any, location: str, errors: list[str], *, required: bool = True) -> None:
    if not isinstance(value, list) or (required and not value):
        add_error(errors, location, "必须是非空相对路径数组" if required else "必须是路径数组")
        return
    for index, path in enumerate(value):
        item = f"{location}[{index}]"
        validate_text(path, item, errors)
        if not is_text(path):
            continue
        normalized = path.replace("\\", "/")
        if normalized.startswith("/") or WINDOWS_ABSOLUTE.match(path):
            add_error(errors, item, "不得使用绝对路径")
        lowered = normalized.lower()
        if ".internal/" in f"{lowered}/" or "/reviews/" in f"/{lowered}/":
            add_error(errors, item, "不得指向内部审查材料")


def validate_status(record: dict[str, Any], location: str, errors: list[str]) -> None:
    status = record.get("status")
    if status not in STATUSES:
        add_error(errors, f"{location}.status", f"必须是 {sorted(STATUSES)}")
    if status == "confirmed":
        validate_evidence_paths(record.get("evidence_paths"), f"{location}.evidence_paths", errors)
    elif status == "unknown":
        validate_text(record.get("next_probe"), f"{location}.next_probe", errors)


def validate_decision_logic(value: Any, location: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        add_error(errors, location, "必须是对象")
        return
    kind = value.get("kind")
    if kind not in LOGIC_KINDS:
        add_error(errors, f"{location}.kind", f"必须是 {sorted(LOGIC_KINDS)}")
    validate_text(value.get("canonical"), f"{location}.canonical", errors)
    terms = value.get("terms")
    if not isinstance(terms, list):
        add_error(errors, f"{location}.terms", "必须是数组")
    elif kind not in {"unknown", "not_applicable"} and not terms:
        add_error(errors, f"{location}.terms", "可执行规则必须至少解释一个符号或输入")
    else:
        for index, term in enumerate(terms):
            term_location = f"{location}.terms[{index}]"
            if not isinstance(term, dict):
                add_error(errors, term_location, "必须是对象")
                continue
            for field in ("symbol", "meaning", "source_locator"):
                validate_text(term.get(field), f"{term_location}.{field}", errors)
            validate_status(term, term_location, errors)
    order = value.get("evaluation_order")
    if not isinstance(order, list) or not order:
        add_error(errors, f"{location}.evaluation_order", "必须是非空数组")
    else:
        for index, step in enumerate(order):
            validate_text(step, f"{location}.evaluation_order[{index}]", errors)
    validate_text(value.get("short_circuit"), f"{location}.short_circuit", errors)
    if kind == "unknown":
        validate_text(value.get("next_probe"), f"{location}.next_probe", errors)


def validate_runtime_sequence(value: Any, location: str, errors: list[str]) -> None:
    if not isinstance(value, list) or not value:
        add_error(errors, location, "必须是非空步骤数组")
        return
    orders: list[int] = []
    step_ids: set[str] = set()
    for index, step in enumerate(value):
        step_location = f"{location}[{index}]"
        if not isinstance(step, dict):
            add_error(errors, step_location, "必须是对象")
            continue
        for field in ("step_id", "trigger", "operation"):
            validate_text(step.get(field), f"{step_location}.{field}", errors)
        step_id = step.get("step_id")
        if is_text(step_id):
            if step_id in step_ids:
                add_error(errors, f"{step_location}.step_id", "必须唯一")
            step_ids.add(step_id)
        order = step.get("order")
        if not isinstance(order, int) or isinstance(order, bool) or order < 1:
            add_error(errors, f"{step_location}.order", "必须是从 1 开始的正整数")
        else:
            orders.append(order)
        inputs = step.get("inputs")
        if not isinstance(inputs, list) or not inputs:
            add_error(errors, f"{step_location}.inputs", "必须是非空数组")
        outputs = step.get("outputs")
        if not isinstance(outputs, list) or not outputs:
            add_error(errors, f"{step_location}.outputs", "每步至少绑定一个输出与消费者")
        else:
            for output_index, output in enumerate(outputs):
                output_location = f"{step_location}.outputs[{output_index}]"
                if not isinstance(output, dict):
                    add_error(errors, output_location, "必须是对象")
                    continue
                for field in ("value", "consumer", "effect"):
                    validate_text(output.get(field), f"{output_location}.{field}", errors)
                consumer_status = output.get("consumer_status")
                if consumer_status not in STATUSES:
                    add_error(errors, f"{output_location}.consumer_status", f"必须是 {sorted(STATUSES)}")
                if consumer_status == "unknown":
                    validate_text(output.get("next_probe"), f"{output_location}.next_probe", errors)
        validate_status(step, step_location, errors)
    if orders and sorted(orders) != list(range(1, len(value) + 1)):
        add_error(errors, location, "order 必须唯一且连续递增")


def validate_tuning_contract(value: Any, location: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        add_error(errors, location, "必须是对象")
        return
    availability = value.get("availability")
    if availability not in TUNING_AVAILABILITY:
        add_error(errors, f"{location}.availability", f"必须是 {sorted(TUNING_AVAILABILITY)}")
        return
    items = value.get("items")
    if not isinstance(items, list):
        add_error(errors, f"{location}.items", "必须是数组")
        return
    if availability == "present" and not items:
        add_error(errors, f"{location}.items", "availability=present 时不能为空")
    if availability == "none":
        validate_text(value.get("reason"), f"{location}.reason", errors)
    if availability == "unknown":
        validate_text(value.get("next_probe"), f"{location}.next_probe", errors)
    for index, item in enumerate(items):
        item_location = f"{location}.items[{index}]"
        if not isinstance(item, dict):
            add_error(errors, item_location, "必须是对象")
            continue
        for field in ("control_locator", "current_value", "change", "direct_effect", "downstream_effect", "tradeoff"):
            validate_text(item.get(field), f"{item_location}.{field}", errors)
        for field in ("value_status", "effect_status"):
            if item.get(field) not in STATUSES:
                add_error(errors, f"{item_location}.{field}", f"必须是 {sorted(STATUSES)}")
        if item.get("control_stage") not in CONTROL_STAGES:
            add_error(errors, f"{item_location}.control_stage", f"必须是 {sorted(CONTROL_STAGES)}")
        if item.get("effect_status") == "unknown" or item.get("control_stage") == "unknown":
            validate_text(item.get("next_probe"), f"{item_location}.next_probe", errors)
        validate_status(item, item_location, errors)


def validate_unknown_edges(value: Any, location: str, errors: list[str]) -> None:
    if not isinstance(value, list):
        add_error(errors, location, "必须是数组")
        return
    for index, edge in enumerate(value):
        edge_location = f"{location}[{index}]"
        if not isinstance(edge, dict):
            add_error(errors, edge_location, "必须是结构化对象，不能再使用自由字符串")
            continue
        for field in ("from", "to", "missing_proof", "impact", "next_probe"):
            validate_text(edge.get(field), f"{edge_location}.{field}", errors)
        if edge.get("status") not in {"unknown", "inferred"}:
            add_error(errors, f"{edge_location}.status", "未知边状态必须是 unknown 或 inferred")


def validate(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["root: 必须是对象"]
    concepts = data.get("concepts")
    claims = data.get("claims")
    if not isinstance(concepts, list) or not concepts:
        add_error(errors, "concepts", "必须是非空数组")
        concepts = []
    if not isinstance(claims, list) or not claims:
        add_error(errors, "claims", "必须是非空数组")
        claims = []

    concept_ids: set[str] = set()
    for index, concept in enumerate(concepts):
        location = f"concepts[{index}]"
        if not isinstance(concept, dict):
            add_error(errors, location, "必须是对象")
            continue
        for field in ("id", "name", "summary", "plain_definition", "config_shape"):
            validate_text(concept.get(field), f"{location}.{field}", errors)
        concept_id = concept.get("id")
        if is_text(concept_id):
            if not concept_id.startswith("concept:"):
                add_error(errors, f"{location}.id", "必须以 concept: 开头")
            if concept_id in concept_ids:
                add_error(errors, f"{location}.id", "必须唯一")
            concept_ids.add(concept_id)
        if concept.get("explanation_contract_version") != "1.1":
            add_error(errors, f"{location}.explanation_contract_version", "必须是 1.1")
        validate_status(concept, location, errors)
        if concept.get("confidence") not in CONFIDENCES:
            add_error(errors, f"{location}.confidence", f"必须是 {sorted(CONFIDENCES)}")
        validate_decision_logic(concept.get("decision_logic"), f"{location}.decision_logic", errors)
        validate_runtime_sequence(concept.get("runtime_sequence"), f"{location}.runtime_sequence", errors)
        validate_tuning_contract(concept.get("tuning_contract"), f"{location}.tuning_contract", errors)
        chain = concept.get("chain_position")
        if not isinstance(chain, dict):
            add_error(errors, f"{location}.chain_position", "必须是对象")
        else:
            validate_unknown_edges(chain.get("unknown_edges"), f"{location}.chain_position.unknown_edges", errors)
            unknown_consumers = [
                output
                for step in concept.get("runtime_sequence", []) if isinstance(step, dict)
                for output in step.get("outputs", []) if isinstance(output, dict)
                if output.get("consumer_status") == "unknown"
            ]
            if unknown_consumers and not chain.get("unknown_edges"):
                add_error(errors, f"{location}.chain_position.unknown_edges", "消费者未知时必须建立结构化未知边")

    claim_ids: set[str] = set()
    for index, claim in enumerate(claims):
        location = f"claims[{index}]"
        if not isinstance(claim, dict):
            add_error(errors, location, "必须是对象")
            continue
        for field in ("id", "statement"):
            validate_text(claim.get(field), f"{location}.{field}", errors)
        claim_id = claim.get("id")
        if is_text(claim_id):
            if not claim_id.startswith("claim:"):
                add_error(errors, f"{location}.id", "必须以 claim: 开头")
            if claim_id in claim_ids:
                add_error(errors, f"{location}.id", "必须唯一")
            claim_ids.add(claim_id)
        validate_status(claim, location, errors)
        if claim.get("confidence") not in CONFIDENCES:
            add_error(errors, f"{location}.confidence", f"必须是 {sorted(CONFIDENCES)}")
        linked = claim.get("concept_ids")
        if not isinstance(linked, list) or not linked:
            add_error(errors, f"{location}.concept_ids", "必须是非空数组")
        else:
            for concept_id in linked:
                if concept_id not in concept_ids:
                    add_error(errors, f"{location}.concept_ids", f"引用不存在的 concept: {concept_id}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("seed", type=Path)
    args = parser.parse_args()
    data = json.loads(args.seed.read_text(encoding="utf-8"))
    errors = validate(data)
    print(json.dumps({
        "status": "failed" if errors else "passed",
        "seed": str(args.seed.resolve()),
        "concepts": len(data.get("concepts", [])) if isinstance(data, dict) else 0,
        "claims": len(data.get("claims", [])) if isinstance(data, dict) else 0,
        "errors": errors,
    }, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
