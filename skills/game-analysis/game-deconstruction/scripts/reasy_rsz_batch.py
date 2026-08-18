#!/usr/bin/env python3
"""Batch-parse layered RE Engine RSZ assets from a selective-extraction manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from reasy_rsz_dump import convert


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reasy-source", required=True, type=Path)
    parser.add_argument("--rsz-dump", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--game-version", required=True, help="Target RE Engine game identifier supported by the selected registry")
    parser.add_argument("--max-depth", type=int, default=12)
    parser.add_argument("--all-layers", action="store_true")
    parser.add_argument("--allow-registry-mismatch", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def layer_precedence(layer: str) -> int:
    match = re.fullmatch(r"patch_(\d+)", layer, re.IGNORECASE)
    return int(match.group(1)) if match else 0


def read_manifest(path: Path, all_layers: bool) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if all_layers:
        return sorted(rows, key=lambda row: (row["asset_path"], layer_precedence(row["layer"])))

    active: dict[str, dict[str, Any]] = {}
    for row in rows:
        current = active.get(row["asset_path"])
        if current is None or layer_precedence(row["layer"]) > layer_precedence(current["layer"]):
            active[row["asset_path"]] = row
    return sorted(active.values(), key=lambda row: row["asset_path"])


def safe_relative(asset_path: str) -> Path:
    relative = Path(asset_path.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"不安全的资产路径：{asset_path}")
    return relative


def main() -> int:
    args = parse_args()
    source = args.reasy_source.resolve()
    output = args.output.resolve()
    if not (source / "file_handlers" / "rsz" / "rsz_file.py").is_file():
        raise SystemExit("--reasy-source 不是可识别的 REasy 源码目录")
    if not args.rsz_dump.is_file() or not args.manifest.is_file():
        raise SystemExit("RSZ dump 或 manifest 不存在")
    if output.exists() and any(output.iterdir()) and not args.overwrite:
        raise SystemExit("输出目录非空；确认后使用 --overwrite")

    sys.path.insert(0, str(source))
    from file_handlers.rsz.rsz_file import RszFile, TypeRegistryValidationError
    from utils.type_registry import TypeRegistry

    registry = TypeRegistry(str(args.rsz_dump))
    rows = read_manifest(args.manifest, args.all_layers)
    rows = [row for row in rows if row["asset_path"].lower().endswith((".user.2", ".pfb.17", ".scn.20"))]
    if args.limit is not None:
        rows = rows[: args.limit]

    output.mkdir(parents=True, exist_ok=True)
    index_path = output / "index.jsonl"
    status_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    resource_edge_count = 0

    with index_path.open("w", encoding="utf-8", newline="\n") as index:
        for number, row in enumerate(rows, 1):
            input_path = Path(row["output_path"])
            asset_relative = safe_relative(row["asset_path"])
            result_path = output / "assets" / row["layer"] / Path(str(asset_relative) + ".json")
            record: dict[str, Any] = {
                "asset_path": row["asset_path"],
                "layer": row["layer"],
                "source_sha256": row["output_sha256"],
                "input_path": str(input_path),
                "output_path": str(result_path),
            }
            try:
                def new_rsz() -> Any:
                    parsed = RszFile()
                    parsed.type_registry = registry
                    parsed.game_version = args.game_version
                    parsed.filepath = str(input_path)
                    return parsed

                data = input_path.read_bytes()
                rsz = new_rsz()
                issues: list[str] = []
                try:
                    rsz.read(data, validate_type_registry=True)
                    validation = "passed"
                except TypeRegistryValidationError as exc:
                    issues = [str(item) for item in exc.issues]
                    if not args.allow_registry_mismatch:
                        raise
                    rsz = new_rsz()
                    rsz.read(data, validate_type_registry=False)
                    validation = "mismatch-allowed"

                instances = []
                local_types: Counter[str] = Counter()
                for instance_id, info in enumerate(rsz.instance_infos):
                    type_info = registry.get_type_info(info.type_id) or {}
                    type_name = type_info.get("name", "<unknown>")
                    local_types[type_name] += 1
                    instances.append(
                        {
                            "instance_id": instance_id,
                            "type_id": f"0x{info.type_id:08X}",
                            "type_name": type_name,
                            "crc": getattr(info, "crc", None),
                            "fields": convert(rsz.parsed_elements.get(instance_id, {}), 0, args.max_depth, set()),
                        }
                    )
                resources = [str(item) for item in getattr(rsz, "resource_infos", [])]
                payload = {
                    "source": str(input_path),
                    "asset_path": row["asset_path"],
                    "layer": row["layer"],
                    "source_sha256": row["output_sha256"],
                    "game_version": args.game_version,
                    "kind": "USR" if rsz.is_usr else "PFB" if rsz.is_pfb else "SCN",
                    "registry_validation": validation,
                    "registry_validation_issues": issues,
                    "resource_paths": resources,
                    "instances": instances,
                }
                result_path.parent.mkdir(parents=True, exist_ok=True)
                result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                record.update(
                    {
                        "status": validation,
                        "instance_count": len(instances),
                        "resource_count": len(resources),
                        "types": dict(local_types),
                    }
                )
                status_counts[validation] += 1
                type_counts.update(local_types)
                resource_edge_count += len(resources)
            except Exception as exc:  # preserve every failed sample in the evidence index
                record.update({"status": "error", "error_type": type(exc).__name__, "error": str(exc)})
                status_counts["error"] += 1
            index.write(json.dumps(record, ensure_ascii=False) + "\n")
            if number % 500 == 0:
                print(json.dumps({"processed": number, "total": len(rows), "status": dict(status_counts)}, ensure_ascii=False))

    summary = {
        "manifest": str(args.manifest.resolve()),
        "mode": "all-layers" if args.all_layers else "active-view",
        "selected_assets": len(rows),
        "status": dict(status_counts),
        "unique_types": len(type_counts),
        "type_instances": sum(type_counts.values()),
        "resource_edges": resource_edge_count,
        "top_types": type_counts.most_common(100),
        "index": str(index_path),
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if status_counts["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
