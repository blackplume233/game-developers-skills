#!/usr/bin/env python3
"""Read-only access layer shared by CLI, HTTP and MCP Agent interfaces."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


DATASETS = {
    "concept": "concepts.jsonl",
    "claim": "claims.jsonl",
    "asset": "assets.jsonl",
    "relation": "relations.jsonl",
    "method": "methods.jsonl",
    "source": "sources.jsonl",
    "chunk": "chunks.jsonl",
}

EVIDENCE_STATUSES = {"confirmed", "inferred", "unknown", "self_build"}
INTERNAL_MARKERS = (".internal/", ".hgoal/", "subagent", "verdict")

# Game-deconstruction vocabulary expansion. This is deliberately small and
# inspectable: it helps bridge planning language, engine language and asset names
# without pretending that lexical expansion is an embedding model.
SYNONYM_GROUPS = (
    ("救援", "救人", "救助", "rescue", "save", "curebadcondition"),
    ("条件", "成立", "前置", "门槛", "判断", "情景", "情境", "决策逻辑", "decision_logic", "situation", "condition", "evaluation"),
    ("怎么做", "如何做", "流程", "步骤", "执行顺序", "runtime_sequence", "sequence"),
    ("调参", "调优", "参数", "阈值", "权重", "优先级", "冷却", "tuning", "tuning_contract"),
    ("目标", "待办", "意图", "goal", "goalplanning", "priority"),
    ("选择", "候选", "决策", "decision", "candidate", "utility", "评分"),
    ("动作", "执行", "行为", "action", "actioninterface", "interact"),
    ("动画", "动作片段", "animation", "motion", "clip"),
    ("感知", "传感", "sensor", "perception", "marker"),
    ("运行时", "代码", "方法", "runtime", "method", "native"),
    ("配置", "资产", "文件", "config", "asset", "user.2"),
    ("未知", "缺口", "未闭合", "unknown", "next_probe"),
)

# These groups are too common to be useful as the only long-query anchor.
# They still affect scoring, but a query that also names rescue, animation,
# perception, a Goal or a Decision must hit one of those more specific groups.
BROAD_ANCHOR_GROUPS = {"条件", "怎么做", "调参", "动作", "运行时", "配置", "未知"}
FALLBACK_STOP_BIGRAMS = {
    "什么", "哪些", "怎么", "如何", "以前", "以后", "先后", "已经", "仍然",
    "不能", "可以", "尤其", "最终", "内容", "结论", "进行", "一个", "当前",
}

SEARCH_FIELDS = {
    "identity": ("id", "name", "title", "statement", "label"),
    "aliases": ("aliases", "tags", "plain_definition", "engineering_identity"),
    "paths": ("path", "asset_path", "evidence_paths", "fields_and_references"),
    "body": (
        "summary", "text", "config_shape", "runtime_contract", "decides",
        "does_not_decide", "planning_impact", "configuration_influence",
        "global_position", "decision_logic", "runtime_sequence", "tuning_contract",
        "chain_position", "limitations", "next_probe", "concept_ids",
    ),
}

COMPACT_FIELDS = (
    "id", "kind", "game", "build", "name", "title", "statement", "summary",
    "status", "confidence", "path", "asset_path", "label", "entry",
    "heading_path", "plain_definition", "engineering_identity", "config_shape",
    "explanation_contract_version", "decision_logic", "runtime_sequence",
    "runtime_contract", "tuning_contract", "decides", "does_not_decide", "chain_position",
    "planning_impact", "configuration_influence", "global_position", "basis",
    "concept_ids", "evidence_ids", "evidence_paths", "limitations", "next_probe",
    "source_asset_id", "target_asset_id", "source_asset_path", "target_asset_path",
    "field_location", "resolved",
)


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().strip()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc
            if isinstance(item, dict):
                records.append(item)
    return records


def _serialized(record: dict[str, Any], fields: Iterable[str]) -> str:
    values: list[str] = []
    for field in fields:
        value = record.get(field)
        if value not in (None, "", []):
            values.append(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))
    return normalize("\n".join(values))


def query_terms(query: str) -> list[str]:
    normalized = normalize(query)
    ascii_terms = re.findall(r"[a-z0-9_.:/-]+", normalized)
    han_runs = re.findall(r"[\u3400-\u9fff]+", normalized)
    terms: list[str] = [normalized] if normalized else []
    terms.extend(ascii_terms)
    active_groups = _active_synonym_groups(normalized)
    if not active_groups:
        for piece in han_runs:
            if 2 <= len(piece) <= 8:
                terms.append(piece)
            if len(piece) >= 3:
                for index in range(min(len(piece) - 1, 12)):
                    bigram = piece[index:index + 2]
                    if bigram not in FALLBACK_STOP_BIGRAMS:
                        terms.append(bigram)
    expanded = list(terms)
    for group in active_groups:
        expanded.extend(group)
    return list(dict.fromkeys(term for term in expanded if len(term) >= 2 or term.isascii()))


def _active_synonym_groups(normalized_query: str) -> list[tuple[str, ...]]:
    groups: list[tuple[str, ...]] = []
    for group in SYNONYM_GROUPS:
        normalized_group = tuple(normalize(item) for item in group)
        if any(alias in normalized_query for alias in normalized_group):
            groups.append(normalized_group)
    return groups


def compact_record(record: dict[str, Any], score: float | None = None, reasons: list[str] | None = None) -> dict[str, Any]:
    result = {key: record[key] for key in COMPACT_FIELDS if record.get(key) not in (None, "", [])}
    if "text" in record:
        text = str(record["text"]).replace("\n", " ").strip()
        result["excerpt"] = text[:700] + ("…" if len(text) > 700 else "")
    if score is not None:
        result["score"] = round(score, 3)
    if reasons:
        result["match_reasons"] = reasons[:8]
    return result


def _trim_context_value(value: Any, depth: int = 0) -> Any:
    if isinstance(value, str):
        return value[:480] + ("…" if len(value) > 480 else "")
    if isinstance(value, list):
        items = [_trim_context_value(item, depth + 1) for item in value[:8]]
        if len(value) > 8:
            items.append(f"… {len(value) - 8} more")
        return items
    if isinstance(value, dict):
        if depth >= 3:
            return {str(key): _trim_context_value(item, depth + 1) for key, item in list(value.items())[:8]}
        return {str(key): _trim_context_value(item, depth + 1) for key, item in list(value.items())[:12]}
    return value


def context_record(record: dict[str, Any]) -> dict[str, Any]:
    fields_by_kind = {
        "concept": (
            "id", "kind", "name", "status", "confidence", "summary", "plain_definition",
            "engineering_identity", "config_shape", "explanation_contract_version",
            "decision_logic", "runtime_sequence", "runtime_contract", "tuning_contract",
            "decides", "does_not_decide", "chain_position", "limitations", "next_probe",
            "evidence_paths",
        ),
        "claim": (
            "id", "kind", "statement", "status", "confidence", "concept_ids", "limitations",
            "next_probe", "evidence_paths",
        ),
        "asset": (
            "id", "kind", "name", "asset_path", "path", "status", "planning_impact",
            "configuration_influence", "global_position", "fields_and_references", "limitations",
            "next_probe", "evidence_paths",
        ),
        "method": (
            "id", "kind", "label", "function_name", "entry", "status", "decompile_status",
            "limitations", "evidence_paths",
        ),
        "chunk": (
            "id", "kind", "title", "heading_path", "path", "status", "evidence_paths",
        ),
        "relation": (
            "id", "kind", "source_asset_id", "target_asset_id", "source_asset_path",
            "target_asset_path", "field_location", "resolved", "status", "evidence_paths",
        ),
    }
    kind = str(record.get("kind", ""))
    fields = fields_by_kind.get(kind, COMPACT_FIELDS)
    result = {
        key: _trim_context_value(record[key])
        for key in fields
        if record.get(key) not in (None, "", [])
    }
    if kind == "asset" and isinstance(record.get("configuration_influence"), list):
        result["configuration_influence"] = [
            {
                key: _trim_context_value(item[key])
                for key in (
                    "field", "planning_control", "effect", "current_values",
                    "occurrences", "sample_complete", "evidence_status",
                )
                if isinstance(item, dict) and item.get(key) not in (None, "", [])
            }
            for item in record["configuration_influence"][:4]
            if isinstance(item, dict)
        ]
        if len(record["configuration_influence"]) > 4:
            result["configuration_influence_more"] = len(record["configuration_influence"]) - 4
    if kind == "chunk" and record.get("text"):
        result["excerpt"] = _trim_context_value(str(record["text"]))
    return result


class AgentKnowledgeBase:
    """In-memory, read-only view over a generated game-deconstruction AKB."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        manifest_path = self.root / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"not an Agent Knowledge Base: {self.root}")
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.records: dict[str, list[dict[str, Any]]] = {
            kind: read_jsonl(self.root / filename) for kind, filename in DATASETS.items()
        }
        self.by_id: dict[str, dict[str, Any]] = {}
        self._search_docs: list[tuple[str, dict[str, Any], dict[str, str]]] = []
        for kind, records in self.records.items():
            for record in records:
                record.setdefault("kind", kind)
                record_id = str(record.get("id", ""))
                if record_id:
                    self.by_id[record_id] = record
                fields = {group: _serialized(record, names) for group, names in SEARCH_FIELDS.items()}
                serialized = "\n".join(fields.values())
                if any(marker in serialized for marker in INTERNAL_MARKERS):
                    raise ValueError(f"internal-only material leaked into Agent KB record: {record_id or kind}")
                self._search_docs.append((kind, record, fields))

    def capabilities(self) -> dict[str, Any]:
        return {
            "schema_version": self.manifest.get("schema_version"),
            "game": self.manifest.get("game"),
            "build": self.manifest.get("build"),
            "counts": self.manifest.get("counts", {}),
            "search_modes": ["hybrid_lexical_graph"],
            "evidence_statuses": sorted(EVIDENCE_STATUSES),
            "operations": ["search", "get_record", "neighbors", "context", "manifest"],
            "read_only": True,
            "evidence_path_base": "workspace_root",
            "release_boundary": self.manifest.get("release_boundary", {}),
        }

    @staticmethod
    def _parse_kinds(kinds: str | Iterable[str] | None) -> set[str]:
        if kinds is None:
            return set(DATASETS)
        values = {item.strip() for item in kinds.split(",")} if isinstance(kinds, str) else {str(item).strip() for item in kinds}
        values.discard("")
        invalid = values - set(DATASETS)
        if invalid:
            raise ValueError(f"unknown kind(s): {', '.join(sorted(invalid))}")
        return values

    def _score(self, phrase: str, terms: list[str], fields: dict[str, str], record: dict[str, Any]) -> tuple[float, list[str]]:
        weights = {"identity": 12.0, "aliases": 9.0, "paths": 6.0, "body": 3.0}
        score = 0.0
        reasons: list[str] = []
        searchable = "\n".join(fields.values())
        if phrase and phrase in searchable:
            score += 32.0
            reasons.append("exact_phrase")
        matched_query_terms = 0
        for term in terms:
            best_group = next((group for group in ("identity", "aliases", "paths", "body") if term in fields[group]), None)
            if best_group:
                score += weights[best_group]
                matched_query_terms += 1
                if len(reasons) < 8:
                    reasons.append(f"{best_group}:{term}")
        if not matched_query_terms:
            return 0.0, []
        score += min(12.0, matched_query_terms * 1.5)
        if record.get("status") == "confirmed":
            score += 2.0
        if record.get("kind") in {"concept", "claim"}:
            score += 1.5
        return score, reasons

    def search(
        self,
        query: str,
        kinds: str | Iterable[str] | None = None,
        status: str | None = None,
        limit: int = 12,
        offset: int = 0,
        full: bool = False,
    ) -> dict[str, Any]:
        phrase = normalize(query)
        if len(phrase) < 2:
            raise ValueError("query must contain at least two characters")
        selected_kinds = self._parse_kinds(kinds)
        if status and status not in EVIDENCE_STATUSES:
            raise ValueError(f"unknown evidence status: {status}")
        limit = min(max(int(limit), 1), 100)
        offset = max(int(offset), 0)
        terms = query_terms(query)
        anchor_groups = [
            group for group in _active_synonym_groups(phrase)
            if group[0] not in BROAD_ANCHOR_GROUPS
        ]
        # Long questions often mention a downstream boundary such as animation.
        # Requiring the first specific intent prevents ubiquitous "does not decide
        # animation" boilerplate from making every asset look relevant. Context()
        # performs small secondary concept/claim probes for the other intents.
        primary_anchor = anchor_groups[:1]
        scored: list[tuple[float, str, dict[str, Any], list[str]]] = []
        for kind, record, fields in self._search_docs:
            if kind not in selected_kinds or (status and record.get("status") != status):
                continue
            if primary_anchor:
                searchable = "\n".join(fields.values())
                if not any(alias in searchable for alias in primary_anchor[0]):
                    continue
            score, reasons = self._score(phrase, terms, fields, record)
            if score:
                scored.append((score, str(record.get("id", "")), record, reasons))
        scored.sort(key=lambda item: (-item[0], item[1]))
        page = scored[offset:offset + limit]
        return {
            "mode": "search",
            "search_mode": "hybrid_lexical_graph",
            "query": query,
            "expanded_terms": terms,
            "kinds": sorted(selected_kinds),
            "status": status,
            "total_count": len(scored),
            "count": len(page),
            "offset": offset,
            "limit": limit,
            "has_more": offset + len(page) < len(scored),
            "next_offset": offset + len(page) if offset + len(page) < len(scored) else None,
            "results": [record if full else compact_record(record, score, reasons) for score, _, record, reasons in page],
        }

    def get_record(self, record_id: str, full: bool = True) -> dict[str, Any]:
        record = self.by_id.get(record_id)
        if record is None:
            raise KeyError(record_id)
        return {"mode": "record", "query": record_id, "count": 1, "results": [record if full else compact_record(record)]}

    def neighbors(self, asset: str, direction: str = "both", limit: int = 50, offset: int = 0, full: bool = False) -> dict[str, Any]:
        if direction not in {"both", "incoming", "outgoing"}:
            raise ValueError("direction must be both, incoming or outgoing")
        needle = normalize(asset)
        matched_ids = {
            str(item.get("id")) for item in self.records["asset"]
            if normalize(str(item.get("id", ""))) == needle or normalize(str(item.get("asset_path", ""))) == needle
        }
        if not matched_ids and needle.startswith("asset:"):
            matched_ids.add(asset)
        relations = []
        for item in self.records["relation"]:
            outgoing = item.get("source_asset_id") in matched_ids
            incoming = item.get("target_asset_id") in matched_ids
            if (direction in {"both", "outgoing"} and outgoing) or (direction in {"both", "incoming"} and incoming):
                relations.append(item)
        limit = min(max(int(limit), 1), 100)
        offset = max(int(offset), 0)
        page = relations[offset:offset + limit]
        return {
            "mode": "neighbors", "query": asset, "direction": direction,
            "matched_asset_ids": sorted(matched_ids), "total_count": len(relations),
            "count": len(page), "offset": offset, "limit": limit,
            "has_more": offset + len(page) < len(relations),
            "next_offset": offset + len(page) if offset + len(page) < len(relations) else None,
            "results": page if full else [compact_record(item) for item in page],
        }

    def context(self, query: str, limit: int = 24) -> dict[str, Any]:
        search = self.search(query, kinds=("concept", "claim", "asset", "method", "chunk"), limit=min(max(limit * 3, 30), 100), full=True)
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in search["results"]:
            grouped[str(record.get("kind", "unknown"))].append(record)

        active_groups = _active_synonym_groups(normalize(query))
        specific_groups = [group for group in active_groups if group[0] not in BROAD_ANCHOR_GROUPS]
        for group in specific_groups[1:]:
            supplemental = self.search(group[0], kinds=("concept", "claim"), limit=2, full=True)
            for record in supplemental["results"]:
                bucket = grouped[str(record.get("kind", "unknown"))]
                if record not in bucket:
                    bucket.append(record)

        referenced_concept_ids = {
            str(concept_id)
            for kind in ("claim", "asset", "method")
            for record in grouped[kind]
            for concept_id in record.get("concept_ids", [])
            if concept_id
        }
        primary_concepts = grouped["concept"][:1]
        linked_concepts = [
            concept for concept in self.records["concept"]
            if str(concept.get("id", "")) in referenced_concept_ids and concept not in primary_concepts
        ]
        remaining_concepts = [
            concept for concept in grouped["concept"]
            if concept not in primary_concepts and concept not in linked_concepts
        ]
        grouped["concept"] = primary_concepts + linked_concepts + remaining_concepts

        concept_ids = {str(item.get("id")) for item in grouped["concept"][:6] if item.get("id")}
        for kind in ("claim", "asset", "method"):
            for item in self.records[kind]:
                linked = set(map(str, item.get("concept_ids", [])))
                if concept_ids & linked and item not in grouped[kind]:
                    grouped[kind].append(item)

        closure_concept_ids = {
            str(concept_id)
            for kind in ("claim", "asset", "method")
            for record in grouped[kind]
            for concept_id in record.get("concept_ids", [])
            if concept_id
        }
        primary_concepts = grouped["concept"][:1]
        closure_concepts = [
            concept for concept in self.records["concept"]
            if str(concept.get("id", "")) in closure_concept_ids and concept not in primary_concepts
        ]
        remaining_concepts = [
            concept for concept in grouped["concept"]
            if concept not in primary_concepts and concept not in closure_concepts
        ]
        grouped["concept"] = primary_concepts + closure_concepts + remaining_concepts
        concept_ids = {str(item.get("id")) for item in grouped["concept"][:6] if item.get("id")}
        for kind in ("claim", "asset", "method"):
            for item in self.records[kind]:
                linked = set(map(str, item.get("concept_ids", [])))
                if concept_ids & linked and item not in grouped[kind]:
                    grouped[kind].append(item)

        runtime_refs = list(dict.fromkeys(
            normalize(str(reference))
            for item in grouped["concept"][:6]
            for reference in item.get("runtime_methods", [])
            if reference
        ))
        ordered_methods: list[dict[str, Any]] = []
        for reference in runtime_refs:
            for method in self.records["method"]:
                label = normalize(str(method.get("label", "")))
                function_name = normalize(str(method.get("function_name", "")))
                entry = normalize(str(method.get("entry", "")))
                reference_name = reference.split("@", 1)[0]
                reference_entry = reference.rsplit("0x", 1)[-1] if "0x" in reference else ""
                if "." in reference_name:
                    name_match = reference_name in label or (label and label in reference_name)
                elif reference_name.startswith("fun_"):
                    name_match = reference_name == function_name
                else:
                    name_match = reference_name == label.rsplit(".", 1)[-1] or reference_name == function_name
                if name_match or (reference_entry and reference_entry == entry):
                    if method not in ordered_methods:
                        ordered_methods.append(method)
                    break
        grouped["method"] = ordered_methods + [method for method in grouped["method"] if method not in ordered_methods]

        priority_asset_paths: list[str] = []
        for concept in grouped["concept"][:6]:
            for field in ("representative_assets", "static_entities"):
                for reference in concept.get(field, []):
                    if not isinstance(reference, dict):
                        continue
                    asset_path = reference.get("logical_path") or reference.get("asset_path")
                    if asset_path:
                        priority_asset_paths.append(normalize(str(asset_path)))
        priority_assets = [
            asset for wanted in dict.fromkeys(priority_asset_paths)
            for asset in self.records["asset"]
            if normalize(str(asset.get("asset_path", ""))) == wanted
        ]
        grouped["asset"] = priority_assets + [asset for asset in grouped["asset"] if asset not in priority_assets]

        caps = {"concept": 6, "claim": 10, "asset": 6, "method": 6, "chunk": 4}
        selected = {kind: [context_record(item) for item in grouped[kind][:cap]] for kind, cap in caps.items()}
        asset_keys = [item.get("asset_path") or item.get("id") for item in grouped["asset"][:4]]
        relations: list[dict[str, Any]] = []
        seen_relations: set[str] = set()
        for key in asset_keys:
            if not key:
                continue
            for relation in self.neighbors(str(key), limit=12, full=True)["results"]:
                relation_id = str(relation.get("id", ""))
                if relation_id not in seen_relations:
                    seen_relations.add(relation_id)
                    relations.append(context_record(relation))

        all_selected = [item for records in selected.values() for item in records]
        evidence_paths = list(dict.fromkeys(
            str(path) for item in all_selected
            for path in list(item.get("evidence_paths", [])) + ([item.get("path")] if item.get("path") else [])
            if not any(marker in normalize(str(path)) for marker in INTERNAL_MARKERS)
        ))
        unknowns = [item for item in all_selected if item.get("status") == "unknown"]
        return {
            "mode": "context",
            "query": query,
            "game": self.manifest.get("game"),
            "build": self.manifest.get("build"),
            "evidence_path_base": "workspace_root",
            "answer_contract": {
                "confirmed": "可以作为当前 build 的事实引用，并保留 evidence_paths。",
                "inferred": "必须保留推断限定语。",
                "unknown": "只描述缺口，并优先使用 next_probe。",
                "self_build": "只用于工程迁移建议，不能证明原游戏实现。",
            },
            "concepts": selected["concept"],
            "claims": selected["claim"],
            "assets": selected["asset"],
            "methods": selected["method"],
            "context_chunks": selected["chunk"],
            "relations": relations[:24],
            "unknowns": unknowns,
            "evidence_paths": evidence_paths,
            "retrieval": {
                "search_mode": search["search_mode"],
                "expanded_terms": search["expanded_terms"],
                "total_matches": search["total_count"],
            },
        }

    def llms_text(self, base_url: str = "") -> str:
        base = base_url.rstrip("/")
        game = self.manifest.get("game", "Game")
        build = self.manifest.get("build", "unknown")
        return "\n".join([
            f"# {game} 白盒拆解知识库",
            "",
            f"> Build {build} 的只读 Agent 入口。优先使用 context 接口取得结论、资产、未知项与证据路径。",
            "> `evidence_paths` 均相对于包含 `analysis-project/` 的 workspace/project 根目录。",
            "",
            "## Agent API",
            f"- [能力与证据契约]({base}/api/agent/capabilities)",
            f"- [OpenAPI 描述]({base}/openapi.json)",
            f"- [搜索示例]({base}/api/agent/search?q=Pawn%20救援)",
            f"- [答案包示例]({base}/api/agent/context?q=Pawn%20救援)",
            f"- [知识库清单]({base}/api/agent/manifest)",
            "",
            "## Reader corpus",
            f"- [WebBook 目录]({base}/api/wiki/tree)",
            f"- [完整 LLM 语料]({base}/llms-full.txt): 仅包含发布白名单章节，不含内部审查。",
            "",
            "## Evidence discipline",
            "- confirmed 可以作为当前 build 的事实引用，但必须保留证据路径。",
            "- inferred 必须保留推断限定语；unknown 只说明缺口；self_build 只表示自研方案。",
        ]) + "\n"

    def llms_full_text(self) -> str:
        header = self.llms_text("")
        sections = [header, "# Published WebBook corpus\n"]
        for item in self.records["chunk"]:
            heading = " / ".join(map(str, item.get("heading_path", []))) or str(item.get("title", "Untitled"))
            text = str(item.get("text", "")).strip()
            if any(marker in normalize(text) for marker in INTERNAL_MARKERS):
                continue
            sections.append(f"## {heading}\n\nSource: {item.get('path', '')}\n\n{text}\n")
        return "\n".join(sections)

    def openapi(self, server_url: str = "http://127.0.0.1:8765") -> dict[str, Any]:
        parameter = lambda name, description, required=False: {
            "name": name, "in": "query", "required": required,
            "description": description, "schema": {"type": "string"},
        }
        paths = {
            "/api/agent/capabilities": {"get": {"operationId": "getAgentCapabilities", "summary": "读取能力、build 与证据契约", "responses": {"200": {"description": "Agent capabilities"}}}},
            "/api/agent/manifest": {"get": {"operationId": "getKnowledgeManifest", "summary": "读取知识库清单与哈希", "responses": {"200": {"description": "Knowledge manifest"}}}},
            "/api/agent/search": {"get": {"operationId": "searchKnowledge", "summary": "跨概念、断言、资产、方法和章节检索", "parameters": [parameter("q", "自然语言、工程术语或资产路径", True), parameter("kind", "逗号分隔的记录类型"), parameter("status", "证据状态"), parameter("limit", "1-100"), parameter("offset", "分页偏移")], "responses": {"200": {"description": "Paginated search results"}}}},
            "/api/agent/record": {"get": {"operationId": "getKnowledgeRecord", "summary": "按稳定 ID 读取完整记录", "parameters": [parameter("id", "稳定记录 ID", True)], "responses": {"200": {"description": "Knowledge record"}, "404": {"description": "Record not found"}}}},
            "/api/agent/neighbors": {"get": {"operationId": "getAssetNeighbors", "summary": "读取资产入边和出边", "parameters": [parameter("asset", "资产 ID 或逻辑路径", True), parameter("direction", "both、incoming 或 outgoing"), parameter("limit", "1-100"), parameter("offset", "分页偏移")], "responses": {"200": {"description": "Paginated relation edges"}}}},
            "/api/agent/context": {"get": {"operationId": "getAnswerContext", "summary": "一次取得回答问题所需的概念、结论、资产、方法、未知项和证据", "parameters": [parameter("q", "自然语言问题", True), parameter("limit", "上下文预算，1-50")], "responses": {"200": {"description": "Evidence-aware answer context"}}}},
        }
        return {
            "openapi": "3.1.0",
            "info": {"title": f"{self.manifest.get('game', 'Game')} Deconstruction Agent API", "version": str(self.manifest.get("build", "1")), "description": "只读、build 绑定、证据状态感知的游戏白盒拆解知识接口。"},
            "servers": [{"url": server_url.rstrip("/")}],
            "paths": paths,
        }
