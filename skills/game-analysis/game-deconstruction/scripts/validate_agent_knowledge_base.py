#!/usr/bin/env python3
"""Validate schema, references and release isolation of an Agent Knowledge Base."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


FILES = ["concepts.jsonl", "claims.jsonl", "assets.jsonl", "relations.jsonl", "methods.jsonl", "sources.jsonl", "chunks.jsonl"]
FORBIDDEN = [
    ".internal/", ".internal\\", ".hgoal/", ".hgoal\\", "/reviews/", "\\reviews\\",
    "feynman verdict", "subagent metadata", "goal audit", "generation log",
]
VALID_STATUS = {"confirmed", "inferred", "unknown", "self_build"}
MECHANISM_LOGIC_KINDS = {
    "boolean_predicate", "numeric_formula", "state_transition", "ordering",
    "mapping", "passthrough", "unknown", "not_applicable",
}


def validate_mechanism_contract(concept: dict[str, Any], location: str, errors: list[str]) -> None:
    """Validate the additive v1.1 explanation contract without rejecting legacy concepts."""
    version = concept.get("explanation_contract_version")
    if version is None:
        return
    if version != "1.1":
        errors.append(f"{location}: unsupported explanation_contract_version {version!r}")
        return

    logic = concept.get("decision_logic")
    if not isinstance(logic, dict):
        errors.append(f"{location}: decision_logic must be an object")
    else:
        if logic.get("kind") not in MECHANISM_LOGIC_KINDS:
            errors.append(f"{location}: invalid decision_logic.kind {logic.get('kind')!r}")
        if not isinstance(logic.get("canonical"), str) or not logic["canonical"].strip():
            errors.append(f"{location}: decision_logic.canonical is required")
        if not isinstance(logic.get("evaluation_order"), list) or not logic["evaluation_order"]:
            errors.append(f"{location}: decision_logic.evaluation_order must be non-empty")

    sequence = concept.get("runtime_sequence")
    if not isinstance(sequence, list) or not sequence:
        errors.append(f"{location}: runtime_sequence must be non-empty")
    else:
        orders = [step.get("order") for step in sequence if isinstance(step, dict)]
        if len(orders) != len(sequence) or sorted(orders) != list(range(1, len(sequence) + 1)):
            errors.append(f"{location}: runtime_sequence.order must be unique and contiguous from 1")
        for step_index, step in enumerate(sequence, 1):
            if not isinstance(step, dict):
                errors.append(f"{location}: runtime_sequence[{step_index}] must be an object")
                continue
            outputs = step.get("outputs")
            if not isinstance(outputs, list) or not outputs:
                errors.append(f"{location}: runtime_sequence[{step_index}].outputs must bind a consumer")
            elif any(not isinstance(output, dict) or not output.get("consumer") for output in outputs):
                errors.append(f"{location}: runtime_sequence[{step_index}] has an output without consumer")

    tuning = concept.get("tuning_contract")
    if not isinstance(tuning, dict) or tuning.get("availability") not in {"present", "none", "unknown"}:
        errors.append(f"{location}: tuning_contract availability must be present, none or unknown")
    elif tuning["availability"] == "present" and not tuning.get("items"):
        errors.append(f"{location}: tuning_contract.items is required when availability=present")
    elif tuning["availability"] == "unknown" and not tuning.get("next_probe"):
        errors.append(f"{location}: tuning_contract.next_probe is required when availability=unknown")

    chain = concept.get("chain_position")
    unknown_edges = chain.get("unknown_edges") if isinstance(chain, dict) else None
    if not isinstance(unknown_edges, list):
        errors.append(f"{location}: chain_position.unknown_edges must be an array")
    else:
        required = {"from", "to", "missing_proof", "impact", "next_probe", "status"}
        for edge_index, edge in enumerate(unknown_edges, 1):
            if not isinstance(edge, dict) or not required.issubset(edge):
                errors.append(f"{location}: unknown_edges[{edge_index}] must be a structured edge")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path, errors: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.is_file():
        errors.append(f"missing: {path.name}")
        return records
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}:{line_number}: invalid JSON: {exc}")
            continue
        if not isinstance(item, dict):
            errors.append(f"{path.name}:{line_number}: record must be an object")
            continue
        records.append(item)
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kb_root", type=Path)
    args = parser.parse_args()
    root = args.kb_root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        print(json.dumps({"status": "failed", "errors": ["missing manifest.json"]}, ensure_ascii=False, indent=2))
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    datasets = {name: read_jsonl(root / name, errors) for name in FILES}

    all_ids: set[str] = set()
    per_file_ids: dict[str, set[str]] = {}
    for name, records in datasets.items():
        ids: set[str] = set()
        for index, record in enumerate(records, 1):
            record_id = record.get("id")
            if not isinstance(record_id, str) or not record_id:
                errors.append(f"{name}:{index}: missing stable id")
                continue
            if record_id in ids or record_id in all_ids:
                errors.append(f"duplicate id: {record_id}")
            ids.add(record_id)
            all_ids.add(record_id)
            if record.get("kind") is None:
                errors.append(f"{name}:{index}: missing kind")
            status = record.get("status")
            if status is not None and status not in VALID_STATUS:
                errors.append(f"{name}:{index}: invalid status {status!r}")
            serialized = json.dumps(record, ensure_ascii=False).lower()
            for marker in FORBIDDEN:
                if marker in serialized:
                    errors.append(f"{name}:{index}: forbidden internal marker {marker!r}")
            if re.search(r"\b[a-z]:\\", serialized, flags=re.IGNORECASE):
                errors.append(f"{name}:{index}: machine-specific absolute path leaked into AKB")
        per_file_ids[name] = ids

    source_ids = per_file_ids.get("sources.jsonl", set())
    asset_ids = per_file_ids.get("assets.jsonl", set())
    for name in ("concepts.jsonl", "claims.jsonl", "chunks.jsonl"):
        for index, record in enumerate(datasets[name], 1):
            for evidence_id in record.get("evidence_ids", []):
                if evidence_id not in source_ids:
                    errors.append(f"{name}:{index}: unresolved evidence id {evidence_id}")

    concept_contract = [
        "plain_definition", "engineering_identity", "not_this", "config_shape", "runtime_contract",
        "decides", "does_not_decide", "chain_position", "worked_examples", "confusions",
    ]
    for index, concept in enumerate(datasets["concepts.jsonl"], 1):
        for field in concept_contract:
            if concept.get(field) in (None, "", [], {}):
                errors.append(f"concepts.jsonl:{index}: missing concept teaching field {field}")
        validate_mechanism_contract(concept, f"concepts.jsonl:{index}", errors)

    asset_learning_contract = ["planning_impact", "configuration_influence", "global_position", "basis"]
    for index, asset in enumerate(datasets["assets.jsonl"], 1):
        for field in asset_learning_contract:
            if asset.get(field) in (None, "", [], {}):
                errors.append(f"assets.jsonl:{index}: missing asset learning field {field}")

    for index, relation in enumerate(datasets["relations.jsonl"], 1):
        if relation.get("source_asset_id") not in asset_ids:
            errors.append(f"relations.jsonl:{index}: missing source asset")
        target_id = relation.get("target_asset_id")
        if relation.get("resolved") and target_id not in asset_ids:
            errors.append(f"relations.jsonl:{index}: resolved target missing from assets")

    forbidden_method_fields = {"c", "decompiled_code", "pseudocode", "raw_bytes"}
    for index, method in enumerate(datasets["methods.jsonl"], 1):
        present = forbidden_method_fields.intersection(method)
        if present:
            errors.append(f"methods.jsonl:{index}: forbidden code field(s): {sorted(present)}")

    expected_counts = manifest.get("counts", {})
    for name, records in datasets.items():
        key = name.removesuffix(".jsonl")
        if expected_counts.get(key) != len(records):
            errors.append(f"manifest count mismatch for {key}: expected {expected_counts.get(key)}, actual {len(records)}")

    expected_hashes = manifest.get("files", {})
    for name in FILES:
        path = root / name
        if path.is_file() and expected_hashes.get(name) != sha256(path):
            errors.append(f"manifest hash mismatch: {name}")

    interface_files = manifest.get("agent_interface_files", {})
    required_interfaces = ["llms.txt", "llms-full.txt", "openapi.json", "agent-access-manifest.json"]
    for name in required_interfaces:
        path = root / name
        if not path.is_file():
            errors.append(f"missing Agent interface file: {name}")
        elif interface_files.get(name) != sha256(path):
            errors.append(f"Agent interface hash mismatch: {name}")
        else:
            serialized = path.read_text(encoding="utf-8", errors="replace").lower()
            for marker in FORBIDDEN:
                if marker in serialized:
                    errors.append(f"{name}: forbidden internal marker {marker!r}")

    workspace_relative = manifest.get("workspace_root", "")
    workspace_root = (root / workspace_relative).resolve() if workspace_relative else None
    if workspace_root:
        for name, snapshot in manifest.get("inputs", {}).items():
            relative = snapshot.get("path", "")
            if not relative or Path(relative).is_absolute():
                errors.append(f"input {name}: path must be workspace-relative")
                continue
            input_path = (workspace_root / relative).resolve()
            try:
                input_path.relative_to(workspace_root)
            except ValueError:
                errors.append(f"input {name}: path escapes workspace")
                continue
            if not input_path.is_file():
                errors.append(f"input {name}: source missing")
            elif sha256(input_path) != snapshot.get("sha256"):
                errors.append(f"input {name}: source hash changed; rebuild required")

    if not datasets["concepts.jsonl"]:
        errors.append("knowledge base has no curated concepts")
    if not datasets["claims.jsonl"]:
        errors.append("knowledge base has no curated claims")
    if not (root / "AGENT-ENTRY.md").is_file():
        errors.append("missing AGENT-ENTRY.md")
    for tool in (
        "agent_kb_access.py", "query_agent_knowledge_base.py",
        "validate_agent_knowledge_base.py", "agent_mcp_server.py",
    ):
        if not (root / "tools" / tool).is_file():
            errors.append(f"missing self-contained tool: tools/{tool}")

    required_capabilities = {
        "hybrid_lexical_graph_search", "pagination", "answer_context",
        "llms_discovery", "openapi_3_1", "mcp_stdio",
    }
    missing_capabilities = required_capabilities - set(manifest.get("capabilities", []))
    if missing_capabilities:
        errors.append(f"manifest missing Agent capabilities: {sorted(missing_capabilities)}")
    if any(item.get("explanation_contract_version") == "1.1" for item in datasets["concepts.jsonl"]):
        if "mechanism_explanation_contract" not in set(manifest.get("capabilities", [])):
            errors.append("manifest missing Agent capability: mechanism_explanation_contract")

    result = {
        "status": "passed" if not errors else "failed",
        "schema_version": manifest.get("schema_version"),
        "game": manifest.get("game"),
        "build": manifest.get("build"),
        "counts": {name.removesuffix(".jsonl"): len(records) for name, records in datasets.items()},
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "errors": [str(exc)]}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(2)
