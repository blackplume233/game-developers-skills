#!/usr/bin/env python3
"""Build a deterministic, local Agent Knowledge Base from a deconstruction project."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from agent_kb_access import AgentKnowledgeBase


SCHEMA_VERSION = "1.0"


def stable_id(prefix: str, *parts: object) -> str:
    raw = "\x1f".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def source_path(project_root: Path, workspace_root: Path, relative: str) -> tuple[Path, str]:
    disk = (project_root / normalize_path(relative)).resolve()
    try:
        public = normalize_path(str(disk.relative_to(workspace_root.resolve())))
    except ValueError:
        public = normalize_path(str(disk.relative_to(project_root.resolve())))
    return disk, public


def flatten_manifest_pages(manifest: dict[str, Any]) -> list[dict[str, str]]:
    metadata: dict[str, dict[str, str]] = {}
    for group in manifest.get("groups", []):
        for page in group.get("pages", []):
            metadata[normalize_path(page["path"])] = {
                "title": page.get("title", ""), "summary": page.get("summary", ""), "group": group.get("id", "")
            }
    order = manifest.get("book", {}).get("reading_order", [])
    pages: list[dict[str, str]] = []
    for raw_path in order:
        path = normalize_path(raw_path)
        item = {"path": path, **metadata.get(path, {})}
        pages.append(item)
    return pages


def split_markdown(text: str) -> list[tuple[str, list[str], str]]:
    chunks: list[tuple[str, list[str], str]] = []
    headings: list[str] = []
    body: list[str] = []

    def flush() -> None:
        cleaned = "\n".join(body).strip()
        if cleaned:
            title = headings[-1] if headings else "导言"
            chunks.append((title, list(headings), cleaned))
        body.clear()

    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        match = None if in_fence else re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            flush()
            level = len(match.group(1))
            headings[:] = headings[: level - 1]
            headings.append(match.group(2).strip())
        else:
            body.append(line)
    flush()
    return chunks


def evidence_statuses(text: str) -> list[str]:
    statuses: list[str] = []
    lowered = text.lower()
    if any(token in lowered for token in ("[已确认]", "[二进制事实", "[解析资产", "已闭合")):
        statuses.append("confirmed")
    if any(token in lowered for token in ("[工程推断]", "[推断]", "可能", "更接近")):
        statuses.append("inferred")
    if any(token in lowered for token in ("[未知]", "尚未闭合", "仍未知", "未知项")):
        statuses.append("unknown")
    if any(token in lowered for token in ("自研", "复刻", "迁移")):
        statuses.append("self_build")
    return statuses


def sanitize_agent_text(text: str) -> str:
    """Remove machine-specific absolute paths while preserving useful local locators."""
    text = re.sub(
        r"([\"'`])([A-Za-z]:\\[^\"'`\r\n]+)\1",
        lambda match: f"{match.group(1)}[LOCAL_PATH]{match.group(1)}",
        text,
    )
    return re.sub(r"\b[A-Za-z]:\\[^\s)\]}>]+", "[LOCAL_PATH]", text)


def read_jsonl_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc
            if not isinstance(item, dict):
                raise ValueError(f"{path}:{line_number}: record must be an object")
            records.append(item)
    return records


def build_sources(
    pages: list[dict[str, str]], project_root: Path, workspace_root: Path, seed: dict[str, Any], native_methods: Path
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    paths: dict[str, dict[str, str]] = {page["path"]: page for page in pages}
    for section in ("concepts", "claims"):
        for item in seed.get(section, []):
            for raw_path in item.get("evidence_paths", []):
                path = normalize_path(raw_path)
                paths.setdefault(path, {"path": path, "title": Path(path).stem, "summary": "seed evidence", "group": "evidence"})
    records: list[dict[str, Any]] = []
    lookup: dict[str, str] = {}
    for path in sorted(paths):
        disk, public = source_path(project_root, workspace_root, path)
        if not disk.is_file():
            raise FileNotFoundError(f"evidence source does not exist: {disk}")
        source_id = stable_id("source:doc", public)
        lookup[path] = source_id
        meta = paths[path]
        records.append({
            "id": source_id, "kind": "source", "source_kind": "published_doc" if path in {p["path"] for p in pages} else "evidence_page",
            "path": public, "title": meta.get("title") or Path(path).stem, "summary": meta.get("summary", ""),
            "sha256": sha256(disk), "restriction": "derived_text_only",
        })
    native_public = normalize_path(str(native_methods.resolve().relative_to(workspace_root.resolve())))
    native_id = stable_id("source:binary-metadata", native_public)
    lookup["@native-methods"] = native_id
    records.append({
        "id": native_id, "kind": "source", "source_kind": "runtime_method_export", "path": native_public,
        "title": "AI native method metadata export", "summary": "Only derived method metadata is admitted to the AKB.",
        "sha256": sha256(native_methods), "restriction": "metadata_only_no_decompiled_body",
    })
    return records, lookup


def enrich_seed_record(
    record: dict[str, Any], kind: str, game: str, build: str, source_lookup: dict[str, str], public_by_source: dict[str, str]
) -> dict[str, Any]:
    result = dict(record)
    result["id"] = record.get("id") or stable_id(kind, record.get("name") or record.get("statement"))
    result["kind"] = kind
    result["game"] = game
    result["build"] = build
    result["schema_version"] = SCHEMA_VERSION
    evidence_paths = [normalize_path(path) for path in record.get("evidence_paths", [])]
    result["evidence_ids"] = [source_lookup[path] for path in evidence_paths]
    result["evidence_paths"] = [public_by_source[source_id] for source_id in result["evidence_ids"]]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True, help="analysis project root")
    parser.add_argument("--workspace-root", type=Path, required=True, help="portable project/workspace root")
    parser.add_argument("--wiki-manifest", type=Path, required=True)
    parser.add_argument("--native-methods", type=Path, required=True)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--game", required=True)
    parser.add_argument("--build", required=True)
    parser.add_argument("--web-root", type=Path, help="Optional WebBook static root for llms/OpenAPI discovery files")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    workspace_root = args.workspace_root.resolve()
    output = args.output.resolve()
    manifest_data = json.loads(args.wiki_manifest.read_text(encoding="utf-8"))
    seed = json.loads(args.seed.read_text(encoding="utf-8"))
    pages = flatten_manifest_pages(manifest_data)
    output.mkdir(parents=True, exist_ok=True)
    (output / "tools").mkdir(exist_ok=True)

    sources, source_lookup = build_sources(pages, project_root, workspace_root, seed, args.native_methods.resolve())
    public_by_source = {item["id"]: item["path"] for item in sources}
    concepts = [enrich_seed_record(item, "concept", args.game, args.build, source_lookup, public_by_source) for item in seed.get("concepts", [])]
    claims = [enrich_seed_record(item, "claim", args.game, args.build, source_lookup, public_by_source) for item in seed.get("claims", [])]

    assets: list[dict[str, Any]] = []
    asset_lookup: dict[str, str] = {}
    analysis_records = read_jsonl_records(project_root / "catalog" / "file-analysis.jsonl")
    learning_by_asset = {
        normalize_path(item["asset_path"]): item.get("learning_card", {})
        for item in analysis_records
        if item.get("asset_path")
    }
    with (project_root / "catalog" / "file-index.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            asset_path = normalize_path(row["asset_path"])
            asset_id = stable_id("asset", asset_path)
            asset_lookup[asset_path] = asset_id
            page = normalize_path(row["page"])
            learning_card = learning_by_asset.get(asset_path, {})
            assets.append({
                "id": asset_id, "kind": "asset", "game": args.game, "build": args.build, "schema_version": SCHEMA_VERSION,
                "asset_path": asset_path, "subsystem": row["subsystem"], "active_layer": row["active_layer"],
                "sha256": row["sha256"], "validation": row["validation"], "status": "confirmed",
                "instance_count": int(row["instance_count"]), "unique_types": int(row["unique_types"]),
                "reference_counts": {"user": int(row["user_ref_count"]), "object": int(row["object_ref_count"]), "resource": int(row["resource_ref_count"])},
                "planning_impact": learning_card.get("planning_impact", ""),
                "configuration_influence": learning_card.get("configuration_influence", []),
                "global_position": learning_card.get("global_position", {}),
                "basis": learning_card.get("basis", {}),
                "path": normalize_path(f"analysis-project/{page}"),
            })

    relations: list[dict[str, Any]] = []
    with (project_root / "catalog" / "resolved-reference-edges.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            source = normalize_path(row["source_asset"])
            target = normalize_path(row["target_normalized"])
            resolved = row["resolved"].strip().lower() == "true"
            relation_id = stable_id("relation", source, row["source_instance"], row["field_location"], target)
            relations.append({
                "id": relation_id, "kind": "relation", "game": args.game, "build": args.build, "schema_version": SCHEMA_VERSION,
                "source_asset_id": asset_lookup.get(source), "target_asset_id": asset_lookup.get(target),
                "source_asset_path": source, "target_asset_path": target, "source_instance": row["source_instance"],
                "source_type": row["source_type"], "field_location": row["field_location"], "target_raw": row["target_raw"],
                "resolved": resolved, "status": "confirmed" if resolved else "unknown",
                "evidence_paths": [normalize_path(f"analysis-project/{row['source_page']}")],
            })

    native = json.loads(args.native_methods.read_text(encoding="utf-8"))
    methods: list[dict[str, Any]] = []
    for method in native.get("methods", []):
        method_id = f"method:{method.get('method_index')}:{method.get('invoke_id')}"
        methods.append({
            "id": method_id, "kind": "method", "game": args.game, "build": args.build, "schema_version": SCHEMA_VERSION,
            "program": native.get("program"), "label": method.get("label"), "method_index": method.get("method_index"),
            "invoke_id": method.get("invoke_id"), "entry": method.get("entry"), "function_name": method.get("function_name"),
            "size": method.get("size"), "callee_count": method.get("callee_count"),
            "decompile_status": "error" if method.get("decompile_error") else "available_not_embedded",
            "decompile_error": method.get("decompile_error") or "", "status": "confirmed",
            "evidence_ids": [source_lookup["@native-methods"]],
            "evidence_paths": [next(item["path"] for item in sources if item["id"] == source_lookup["@native-methods"])],
        })

    chunks: list[dict[str, Any]] = []
    for page in pages:
        disk, public = source_path(project_root, workspace_root, page["path"])
        source_id = source_lookup[page["path"]]
        for index, (title, heading_path, text) in enumerate(split_markdown(disk.read_text(encoding="utf-8")), 1):
            text = sanitize_agent_text(text)
            chunk_id = stable_id("chunk", public, index, " / ".join(heading_path))
            chunks.append({
                "id": chunk_id, "kind": "chunk", "game": args.game, "build": args.build, "schema_version": SCHEMA_VERSION,
                "title": title, "heading_path": heading_path, "text": text, "path": public,
                "source_id": source_id, "evidence_ids": [source_id], "evidence_paths": [public],
                "evidence_statuses": evidence_statuses(text), "status": "confirmed" if "confirmed" in evidence_statuses(text) else "inferred" if "inferred" in evidence_statuses(text) else "unknown" if "unknown" in evidence_statuses(text) else "self_build" if "self_build" in evidence_statuses(text) else None,
            })

    records_by_file = {
        "concepts.jsonl": concepts, "claims.jsonl": claims, "assets.jsonl": assets,
        "relations.jsonl": relations, "methods.jsonl": methods, "sources.jsonl": sources, "chunks.jsonl": chunks,
    }
    counts: dict[str, int] = {}
    file_hashes: dict[str, str] = {}
    for name, records in records_by_file.items():
        counts[name.removesuffix(".jsonl")] = write_jsonl(output / name, records)
        file_hashes[name] = sha256(output / name)

    script_dir = Path(__file__).resolve().parent
    tool_names = (
        "agent_kb_access.py",
        "query_agent_knowledge_base.py",
        "validate_agent_knowledge_base.py",
        "agent_mcp_server.py",
    )
    for tool in tool_names:
        shutil.copy2(script_dir / tool, output / "tools" / tool)

    corpus_digest = hashlib.sha256("".join(f"{name}:{file_hashes[name]}\n" for name in sorted(file_hashes)).encode("utf-8")).hexdigest()
    workspace_metadata_path = workspace_root / "workspace-manifest.json"
    workspace_metadata = json.loads(workspace_metadata_path.read_text(encoding="utf-8")) if workspace_metadata_path.is_file() else {}
    binary_identity_path = workspace_root / "binary-analysis" / "case" / "source-binary.json"
    binary_identity = json.loads(binary_identity_path.read_text(encoding="utf-8")) if binary_identity_path.is_file() else {}
    input_paths = {
        "knowledge_seed": args.seed.resolve(),
        "wiki_manifest": args.wiki_manifest.resolve(),
        "asset_index": project_root / "catalog" / "file-index.csv",
        "reference_edges": project_root / "catalog" / "resolved-reference-edges.csv",
        "native_methods": args.native_methods.resolve(),
    }
    input_snapshots = {
        name: {
            "path": normalize_path(str(path.relative_to(workspace_root))),
            "sha256": sha256(path),
        }
        for name, path in input_paths.items()
    }
    manifest = {
        "schema_version": SCHEMA_VERSION, "knowledge_base_type": "game-deconstruction-agent-kb",
        "game": args.game, "build": args.build, "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": {
            "game": args.game, "app_id": workspace_metadata.get("game", {}).get("steam_app_id"),
            "build_id": args.build, "executable_version": workspace_metadata.get("game", {}).get("executable_version"),
            "executable_sha256": binary_identity.get("sha256"),
        },
        "generator": {"script": "build_agent_knowledge_base.py", "sha256": sha256(Path(__file__).resolve())},
        "workspace_root": "../..", "inputs": input_snapshots,
        "evidence_path_base": "workspace_root",
        "corpus_sha256": corpus_digest, "counts": counts, "files": file_hashes,
        "capabilities": [
            "hybrid_lexical_graph_search", "kind_filter", "status_filter", "pagination",
            "exact_id", "asset_neighbors", "evidence_trace", "answer_context",
            "mechanism_explanation_contract", "llms_discovery", "openapi_3_1", "mcp_stdio",
        ],
        "evidence_statuses": ["confirmed", "inferred", "unknown", "self_build"],
        "release_boundary": {"raw_proprietary_assets": False, "decompiled_bodies": False, "internal_reviews": False, "published_reader_chunks_only": True},
        "entry": "AGENT-ENTRY.md",
        "query_tool": "tools/query_agent_knowledge_base.py",
        "validator": "tools/validate_agent_knowledge_base.py",
        "mcp_server": "tools/agent_mcp_server.py",
        "mcp_transport": "stdio",
        "agent_interfaces": {
            "llms": "llms.txt", "llms_full": "llms-full.txt", "openapi": "openapi.json",
            "access_manifest": "agent-access-manifest.json",
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    entry = f"""# {args.game} Agent Knowledge Base\n\n这是 {args.game} Build {args.build} 白盒拆解的机器入口。先读 `manifest.json`；回答设计或实现问题时优先使用 `--context`，再沿 `evidence_paths` 回到 WebBook 或逐文件证据页。所有 `evidence_paths` 都相对于包含 `analysis-project/` 的 workspace/project 根目录，不相对于当前 `knowledge-base/` 目录。\n\n## CLI 查询\n\n```powershell\npython tools/query_agent_knowledge_base.py . --context \"[自然语言问题]\" --limit 24\npython tools/query_agent_knowledge_base.py . --query \"[概念、工程术语或资产路径]\" --kind concept,claim,asset,method\npython tools/query_agent_knowledge_base.py . --query \"[尚未闭合的环节]\" --status unknown\npython tools/query_agent_knowledge_base.py . --id [稳定记录ID] --full\npython tools/query_agent_knowledge_base.py . --neighbors \"[资产ID或逻辑路径]\" --direction both\n```\n\n命令在本目录执行，输出始终为 JSON。`concepts.jsonl` 和 `claims.jsonl` 是事实优先入口；`chunks.jsonl` 只提供语境；`assets.jsonl`、`relations.jsonl`、`methods.jsonl` 用于证据回绑。\n\n## 标准入口\n\n- `llms.txt`：Agent 发现入口。\n- `openapi.json`：WebBook 只读 Agent API 的 OpenAPI 3.1 描述。\n- `tools/agent_mcp_server.py`：本地 stdio MCP 服务；设置 `GAME_DECONSTRUCTION_KB` 后由 MCP 客户端启动。\n\n## 证据纪律\n\n- `confirmed`：可作为当前 build 的事实引用，但仍带上 `evidence_paths`。\n- `inferred`：保留“推断/更可能”等限定语，不升级为事实。\n- `unknown`：只描述尚未闭合的连接，并优先查看 `next_probe`。\n- `self_build`：是自研迁移方案，不能反向证明原游戏实现。\n\n任何 build、EXE 哈希或活动资产集合变化都应重建本库。知识库不包含原始专有资源、完整反编译正文或生成期独立审查材料。\n"""
    (output / "AGENT-ENTRY.md").write_text(entry, encoding="utf-8", newline="\n")

    access = AgentKnowledgeBase(output)
    discovery_files = {
        "llms.txt": access.llms_text(),
        "llms-full.txt": access.llms_full_text(),
        "openapi.json": json.dumps(access.openapi(), ensure_ascii=False, indent=2) + "\n",
        "agent-access-manifest.json": json.dumps({
            "schema_version": "1.0",
            "game": args.game,
            "build": args.build,
            "corpus_sha256": corpus_digest,
            "read_only": True,
            "query_core": "tools/agent_kb_access.py",
            "cli": "tools/query_agent_knowledge_base.py",
            "mcp": {"server": "tools/agent_mcp_server.py", "transport": "stdio"},
            "http": {"namespace": "/api/agent", "openapi": "/openapi.json"},
            "search_mode": "hybrid_lexical_graph",
            "evidence_path_base": "workspace_root",
            "evidence_statuses": ["confirmed", "inferred", "unknown", "self_build"],
        }, ensure_ascii=False, indent=2) + "\n",
    }
    for name, content in discovery_files.items():
        (output / name).write_text(content, encoding="utf-8", newline="\n")

    web_root = args.web_root.resolve() if args.web_root else (workspace_root / "explorer")
    if web_root.is_dir():
        for name, content in discovery_files.items():
            (web_root / name).write_text(content, encoding="utf-8", newline="\n")

    manifest["agent_interface_files"] = {
        name: sha256(output / name) for name in discovery_files
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "built", "output": str(output), "counts": counts, "corpus_sha256": corpus_digest}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
