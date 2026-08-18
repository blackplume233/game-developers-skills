#!/usr/bin/env python3
"""Query a local Agent Knowledge Base and emit machine-readable JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent_kb_access import AgentKnowledgeBase


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kb_root", type=Path, help="knowledge-base directory")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--query", help="hybrid lexical/graph query")
    group.add_argument("--id", dest="record_id", help="exact stable record ID")
    group.add_argument("--neighbors", help="asset ID or logical asset path")
    group.add_argument(
        "--context",
        help="build an evidence-aware answer context, including decision logic, runtime sequence and tuning contract",
    )
    parser.add_argument("--kind", help="comma-separated kinds")
    parser.add_argument("--status", choices=["confirmed", "inferred", "unknown", "self_build"])
    parser.add_argument("--direction", choices=["both", "incoming", "outgoing"], default="both")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--full", action="store_true", help="return complete records")
    args = parser.parse_args()

    kb = AgentKnowledgeBase(args.kb_root)
    if args.neighbors:
        payload = kb.neighbors(args.neighbors, args.direction, args.limit, args.offset, args.full)
    elif args.record_id:
        payload = kb.get_record(args.record_id, args.full)
    elif args.context:
        payload = kb.context(args.context, args.limit)
    else:
        payload = kb.search(args.query or "", args.kind, args.status, args.limit, args.offset, args.full)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyError as exc:
        print(json.dumps({"error": f"record not found: {exc.args[0]}"}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
