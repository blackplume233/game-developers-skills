#!/usr/bin/env python3
"""Classify a game path list into deconstruction domains and emit a reproducible index."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path


RULES = {
    "ai": re.compile(r"(^|/)(ai|behavior|decision|goal|situation|sensor|personality|formation|nav|waypoint)(/|[_.])", re.I),
    "skills": re.compile(r"(^|/)(skill|ability|action|attack|damage|hit|status|job)(/|[_.])", re.I),
    "animation": re.compile(r"(^|/|[_.])(motion|mot|motlist|motbank|fsm|clip|timeline|rig|skeleton|retarget|chain)(/|[_.])", re.I),
    "rendering": re.compile(r"(^|/|[_.])(mesh|material|mdf|tex|texture|shader|render|effect|efx|light|probe|lod)(/|[_.])", re.I),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-list", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    paths = []
    with args.input_list.open("r", encoding="utf-8-sig", errors="replace") as stream:
        for raw in stream:
            path = raw.strip().replace("\\", "/")
            if path:
                paths.append(path)

    rows = []
    domains = Counter()
    extensions = Counter()
    for path in sorted(set(paths)):
        matched = [name for name, rule in RULES.items() if rule.search(path)]
        suffixes = Path(path).name.lower().split(".")
        if len(suffixes) >= 3 and suffixes[-1].isdigit():
            resource_type = "." + suffixes[-2]
        else:
            resource_type = Path(path).suffix.lower() or "<none>"
        extensions[resource_type] += 1
        if not matched:
            continue
        for domain in matched:
            domains[domain] += 1
        rows.append({"path": path, "domains": ";".join(matched), "resource_type": resource_type})

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "candidates.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["path", "domains", "resource_type"])
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "unique_paths": len(set(paths)),
        "candidate_rows": len(rows),
        "domain_matches": dict(domains),
        "top_resource_types": extensions.most_common(50),
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
