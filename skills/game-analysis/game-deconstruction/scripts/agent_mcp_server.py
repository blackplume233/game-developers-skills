#!/usr/bin/env python3
"""Local read-only MCP server for a game-deconstruction Agent Knowledge Base."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Annotated, Any

from agent_kb_access import AgentKnowledgeBase

try:
    from mcp.types import ToolAnnotations
    from pydantic import Field
    try:
        from mcp.server import MCPServer as MCPServerClass
        MCP_SDK_LINE = "2.x"
    except ImportError:
        from mcp.server.fastmcp import FastMCP as MCPServerClass
        MCP_SDK_LINE = "1.x"
except ImportError as exc:  # pragma: no cover - exercised by installation checks
    print(
        "MCP runtime is missing. Install with: python -m pip install 'mcp>=2,<3'",
        file=sys.stderr,
    )
    raise SystemExit(3) from exc


def locate_kb_root(explicit: str | None = None) -> Path:
    candidates = [
        explicit,
        os.environ.get("GAME_DECONSTRUCTION_KB"),
        str(Path(__file__).resolve().parents[1]),
    ]
    for candidate in candidates:
        if candidate and (Path(candidate).expanduser().resolve() / "manifest.json").is_file():
            return Path(candidate).expanduser().resolve()
    raise FileNotFoundError(
        "Agent Knowledge Base not found. Set GAME_DECONSTRUCTION_KB or pass --kb-root."
    )


def command_line_kb_root() -> str | None:
    for index, argument in enumerate(sys.argv[1:]):
        if argument == "--kb-root" and index + 2 <= len(sys.argv[1:]):
            return sys.argv[index + 2]
        if argument.startswith("--kb-root="):
            return argument.split("=", 1)[1]
    return None


KB_ROOT = locate_kb_root(command_line_kb_root())
KB = AgentKnowledgeBase(KB_ROOT)
READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

mcp = MCPServerClass(
    "game_deconstruction_mcp",
    instructions=(
        "Read-only access to a build-bound game deconstruction knowledge base. "
        "Use context first for an answer pack; preserve confirmed/inferred/unknown/self_build semantics."
    ),
)


@mcp.tool(
    name="game_deconstruction_search",
    title="Search Game Deconstruction Knowledge",
    annotations=READ_ONLY,
    structured_output=True,
)
def game_deconstruction_search(
    query: Annotated[str, Field(description="Natural-language question, engine term or asset path", min_length=2, max_length=500)],
    kind: Annotated[str, Field(description="Optional comma-separated concept,claim,asset,relation,method,source,chunk kinds", max_length=120)] = "",
    status: Annotated[str, Field(description="Optional confirmed, inferred, unknown or self_build status", max_length=20)] = "",
    limit: Annotated[int, Field(description="Maximum records to return", ge=1, le=100)] = 12,
    offset: Annotated[int, Field(description="Pagination offset", ge=0)] = 0,
) -> dict[str, Any]:
    """Search concepts, atomic claims, assets, relations, methods and reader chunks.

    Returns paginated structured records with evidence status, evidence paths and match reasons.
    This tool never reads raw proprietary files or decompiled function bodies.
    """
    return KB.search(query, kind or None, status or None, limit, offset)


@mcp.tool(
    name="game_deconstruction_get_record",
    title="Get Game Deconstruction Record",
    annotations=READ_ONLY,
    structured_output=True,
)
def game_deconstruction_get_record(
    record_id: Annotated[str, Field(description="Stable record ID returned by search", min_length=3, max_length=500)],
) -> dict[str, Any]:
    """Read one complete knowledge record by stable ID, including evidence and limitations."""
    return KB.get_record(record_id, full=True)


@mcp.tool(
    name="game_deconstruction_get_context",
    title="Build Evidence-Aware Answer Context",
    annotations=READ_ONLY,
    structured_output=True,
)
def game_deconstruction_get_context(
    query: Annotated[str, Field(description="Question to assemble evidence for", min_length=2, max_length=500)],
    limit: Annotated[int, Field(description="Retrieval budget before per-kind compaction", ge=4, le=50)] = 24,
) -> dict[str, Any]:
    """Return a compact answer pack of concepts, claims, assets, methods, relations, unknowns and evidence paths.

    Prefer this tool when answering a design or implementation question. It preserves the build and
    evidence-status contract so an Agent does not accidentally turn inference into fact.
    """
    return KB.context(query, limit)


@mcp.tool(
    name="game_deconstruction_get_asset_neighbors",
    title="Trace Game Asset References",
    annotations=READ_ONLY,
    structured_output=True,
)
def game_deconstruction_get_asset_neighbors(
    asset: Annotated[str, Field(description="Asset stable ID or logical path", min_length=3, max_length=1000)],
    direction: Annotated[str, Field(description="both, incoming or outgoing", pattern="^(both|incoming|outgoing)$")] = "both",
    limit: Annotated[int, Field(description="Maximum relation edges", ge=1, le=100)] = 50,
    offset: Annotated[int, Field(description="Pagination offset", ge=0)] = 0,
) -> dict[str, Any]:
    """Trace incoming and outgoing field-level references for one indexed asset."""
    return KB.neighbors(asset, direction, limit, offset)


@mcp.tool(
    name="game_deconstruction_get_manifest",
    title="Get Knowledge Base Manifest",
    annotations=READ_ONLY,
    structured_output=True,
)
def game_deconstruction_get_manifest() -> dict[str, Any]:
    """Return build identity, corpus hashes, counts, capabilities and release boundaries."""
    return {"manifest": KB.manifest, "capabilities": KB.capabilities()}


@mcp.resource(
    "game-deconstruction://manifest",
    name="game_deconstruction_manifest",
    title="Game Deconstruction Manifest",
    description="Build identity, corpus hashes and evidence/release contracts.",
    mime_type="application/json",
)
def manifest_resource() -> str:
    return json.dumps({"manifest": KB.manifest, "capabilities": KB.capabilities()}, ensure_ascii=False, indent=2)


@mcp.resource(
    "game-deconstruction://record/{record_id}",
    name="game_deconstruction_record",
    title="Game Deconstruction Record",
    description="A complete knowledge record addressed by stable ID.",
    mime_type="application/json",
)
def record_resource(record_id: str) -> str:
    return json.dumps(KB.get_record(record_id, full=True), ensure_ascii=False, indent=2)


@mcp.resource(
    "game-deconstruction://llms",
    name="game_deconstruction_llms",
    title="LLM Discovery Guide",
    description="Concise discovery and evidence-discipline guide.",
    mime_type="text/markdown",
)
def llms_resource() -> str:
    return KB.llms_text()


def self_test() -> int:
    capabilities = KB.capabilities()
    probe = KB.search("配置", limit=3)
    context = KB.context("动画 未知", limit=8)
    payload = {
        "status": "passed",
        "server": "game_deconstruction_mcp",
        "mcp_sdk_line": MCP_SDK_LINE,
        "kb_root": str(KB_ROOT),
        "tools": 5,
        "resources": 3,
        "build": capabilities.get("build"),
        "search_results": probe.get("count"),
        "context_evidence_paths": len(context.get("evidence_paths", [])),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--kb-root", help="Override the knowledge-base directory")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.kb_root:
        KB_ROOT = locate_kb_root(args.kb_root)
        KB = AgentKnowledgeBase(KB_ROOT)
    if args.self_test:
        raise SystemExit(self_test())
    mcp.run(transport="stdio")
