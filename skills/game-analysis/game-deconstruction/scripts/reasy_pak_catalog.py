#!/usr/bin/env python3
"""Catalog every entry in layered RE Engine PAKs while preserving unresolved hashes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reasy-source", required=True, type=Path)
    parser.add_argument("--game-dir", required=True, type=Path)
    parser.add_argument("--file-list", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--base-only", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def pak_sort_key(path: Path) -> tuple[int, str]:
    match = re.search(r"patch_(\d+)", path.name, re.IGNORECASE)
    return (int(match.group(1)) if match else 0, path.name.lower())


def main() -> int:
    args = parse_args()
    source = args.reasy_source.resolve()
    game_dir = args.game_dir.resolve()
    output = args.output.resolve()
    if not (source / "file_handlers" / "pak" / "pakfile.py").is_file():
        raise SystemExit("--reasy-source 不是可识别的 REasy 源码目录")
    if not game_dir.is_dir() or not args.file_list.is_file():
        raise SystemExit("游戏目录或路径表不存在")
    if is_relative_to(output, game_dir):
        raise SystemExit("输出目录不能位于游戏安装目录内")
    if output.exists() and any(output.iterdir()) and not args.overwrite:
        raise SystemExit("输出目录非空；确认后使用 --overwrite")

    sys.path.insert(0, str(source))
    from file_handlers.pak.pakfile import PakFile
    from file_handlers.pak.utils import filepath_hash

    known_paths: dict[int, str] = {}
    with args.file_list.open("r", encoding="utf-8-sig", errors="replace") as stream:
        for raw in stream:
            candidate = raw.strip().replace("\\", "/")
            if candidate:
                known_paths[filepath_hash(candidate)] = candidate

    paks = sorted(game_dir.glob("re_chunk_000*.pak"), key=pak_sort_key)
    if args.base_only:
        paks = [path for path in paks if "patch_" not in path.name.lower()]
    if not paks:
        raise SystemExit("没有找到 re_chunk_000*.pak")

    output.mkdir(parents=True, exist_ok=True)
    catalog_path = output / "entries.jsonl"
    layer_counts: Counter[str] = Counter()
    resolution_counts: Counter[str] = Counter()
    compression_counts: Counter[str] = Counter()
    total_compressed = 0
    total_decompressed = 0

    with catalog_path.open("w", encoding="utf-8", newline="\n") as catalog:
        for pak_path in paks:
            pak = PakFile()
            pak.filepath = str(pak_path)
            with pak_path.open("rb") as stream:
                # Read the entire table first. Passing expected_paths to REasy would
                # filter unresolved hashes and violate this catalog's evidence goal.
                pak.read_contents(stream)
            match = re.search(r"patch_(\d+)", pak_path.name, re.IGNORECASE)
            layer = f"patch_{int(match.group(1)):03d}" if match else "base"
            for entry in pak.entries:
                asset_path = known_paths.get(entry.combined_hash)
                resolution = "known" if asset_path else "unknown"
                record = {
                    "source_pak": str(pak_path),
                    "source_pak_size": pak_path.stat().st_size,
                    "layer": layer,
                    "asset_path": asset_path,
                    "name_resolution": resolution,
                    "combined_hash": f"{entry.combined_hash:016X}",
                    "offset": entry.offset,
                    "compressed_size": entry.compressed_size,
                    "decompressed_size": entry.decompressed_size,
                    "compression": entry.compression,
                    "resource_encryption": entry.encryption,
                    "pak_version": f"{pak.header.major}.{pak.header.minor}" if pak.header else None,
                    "pak_flags": pak.header.feature_flags if pak.header else None,
                }
                catalog.write(json.dumps(record, ensure_ascii=False) + "\n")
                layer_counts[layer] += 1
                resolution_counts[resolution] += 1
                compression_counts[str(entry.compression)] += 1
                total_compressed += int(entry.compressed_size)
                total_decompressed += int(entry.decompressed_size)

    summary = {
        "pak_count": len(paks),
        "known_path_candidates": len(known_paths),
        "entry_count": sum(layer_counts.values()),
        "layers": dict(layer_counts),
        "name_resolution": dict(resolution_counts),
        "compression": dict(compression_counts),
        "total_compressed_bytes": total_compressed,
        "total_decompressed_bytes": total_decompressed,
        "estimated_expansion_ratio": (total_decompressed / total_compressed) if total_compressed else None,
        "catalog": str(catalog_path),
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
