#!/usr/bin/env python3
"""Protocol smoke test for the generated read-only Agent MCP server."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def run_test(kb_root: Path, server: Path, query: str) -> dict:
    environment = dict(os.environ)
    environment["GAME_DECONSTRUCTION_KB"] = str(kb_root)
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-B", str(server)],
        cwd=str(kb_root),
        env=environment,
    )
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            initialized = await session.initialize()
            tools = await session.list_tools()
            resources = await session.list_resources()
            templates = await session.list_resource_templates()
            result = await session.call_tool(
                "game_deconstruction_get_context",
                {"query": query, "limit": 8},
            )
            manifest_resource = await session.read_resource("game-deconstruction://manifest")

    structured = getattr(result, "structuredContent", None) or getattr(result, "structured_content", None)
    tool_names = [tool.name for tool in tools.tools]
    required_tools = {
        "game_deconstruction_search",
        "game_deconstruction_get_record",
        "game_deconstruction_get_context",
        "game_deconstruction_get_asset_neighbors",
        "game_deconstruction_get_manifest",
    }
    if not required_tools.issubset(tool_names):
        raise AssertionError(f"missing MCP tools: {sorted(required_tools - set(tool_names))}")
    if getattr(result, "isError", getattr(result, "is_error", False)):
        raise AssertionError("MCP context tool returned an error")
    if not isinstance(structured, dict) or not structured.get("evidence_paths"):
        raise AssertionError("MCP context tool did not return structured evidence")
    if any(".internal" in str(path).lower() for path in structured.get("evidence_paths", [])):
        raise AssertionError("MCP response leaked internal evidence")
    if not manifest_resource.contents:
        raise AssertionError("MCP manifest resource is empty")

    resource_templates = getattr(templates, "resource_templates", None)
    if resource_templates is None:
        resource_templates = getattr(templates, "resourceTemplates", [])

    def template_uri(template: object) -> str:
        value = getattr(template, "uri_template", None)
        if value is None:
            value = getattr(template, "uriTemplate", "")
        return str(value)

    return {
        "status": "passed",
        "protocol": str(getattr(initialized, "protocolVersion", getattr(initialized, "protocol_version", ""))),
        "tools": tool_names,
        "resources": [str(resource.uri) for resource in resources.resources],
        "resource_templates": [template_uri(template) for template in resource_templates],
        "structured_output": True,
        "build": structured.get("build"),
        "claims": len(structured.get("claims", [])),
        "evidence_paths": len(structured.get("evidence_paths", [])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kb_root", type=Path)
    parser.add_argument("--server", type=Path)
    parser.add_argument("--query", default="核心行为怎样从配置进入运行时")
    args = parser.parse_args()
    root = args.kb_root.resolve()
    server = (args.server or root / "tools" / "agent_mcp_server.py").resolve()
    payload = asyncio.run(run_test(root, server, args.query))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
