#!/usr/bin/env python3
"""Selectively extract known paths from RE Engine PAKs via an external REasy source tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reasy-source", required=True, type=Path)
    parser.add_argument("--game-dir", required=True, type=Path)
    parser.add_argument("--file-list", required=True, type=Path)
    parser.add_argument("--regex", action="append", default=[])
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--base-only", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pak_sort_key(path: Path) -> tuple[int, str]:
    match = re.search(r"patch_(\d+)", path.name, re.IGNORECASE)
    return (int(match.group(1)) if match else 0, path.name.lower())


def main() -> int:
    args = parse_args()
    source = args.reasy_source.resolve()
    game_dir = args.game_dir.resolve()
    output = args.output.resolve()

    if not source.is_dir() or not (source / "file_handlers" / "pak" / "pakfile.py").is_file():
        raise SystemExit("--reasy-source 不是可识别的 REasy 源码目录")
    if not game_dir.is_dir():
        raise SystemExit("--game-dir 不存在")
    if is_relative_to(output, game_dir):
        raise SystemExit("输出目录不能位于游戏安装目录内")
    if output.exists() and any(output.iterdir()) and not args.overwrite and not args.dry_run:
        raise SystemExit("输出目录非空；确认后使用 --overwrite")

    patterns = [re.compile(item, re.IGNORECASE) for item in args.regex]
    exact = {item.strip().replace("\\", "/") for item in args.path if item.strip()}
    known_paths = []
    with args.file_list.open("r", encoding="utf-8-sig", errors="replace") as stream:
        for raw in stream:
            candidate = raw.strip().replace("\\", "/")
            if not candidate:
                continue
            if candidate in exact or any(pattern.search(candidate) for pattern in patterns):
                known_paths.append(candidate)
    known_paths = sorted(set(known_paths))
    if not known_paths:
        raise SystemExit("筛选条件没有命中路径列表")

    paks = sorted(game_dir.glob("re_chunk_000*.pak"), key=pak_sort_key)
    if args.base_only:
        paks = [path for path in paks if "patch_" not in path.name.lower()]
    if not paks:
        raise SystemExit("游戏目录中没有找到 re_chunk_000*.pak")

    if args.dry_run:
        print(json.dumps({"paths": len(known_paths), "paks": [str(p) for p in paks]}, ensure_ascii=False, indent=2))
        return 0

    sys.path.insert(0, str(source))
    try:
        from file_handlers.pak.pakfile import PakFile
        from file_handlers.pak.utils import filepath_hash
    except ModuleNotFoundError as exc:
        raise SystemExit(f"REasy 依赖缺失：{exc}；请在独立虚拟环境安装其 requirements") from exc

    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.jsonl"
    expected_paths = {filepath_hash(path): path for path in known_paths}
    extracted = 0

    with manifest_path.open("w", encoding="utf-8", newline="\n") as manifest:
        for pak_path in paks:
            pak = PakFile()
            pak.filepath = str(pak_path)
            with pak_path.open("rb") as stream:
                pak.read_contents(stream, expected_paths)
            layer = "base"
            match = re.search(r"patch_(\d+)", pak_path.name, re.IGNORECASE)
            if match:
                layer = f"patch_{int(match.group(1)):03d}"
            for entry in pak.entries:
                if not entry.path:
                    continue
                target = output / "layers" / layer / entry.path
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() and not args.overwrite:
                    raise SystemExit(f"输出已存在：{target}")
                with target.open("wb") as out_stream:
                    pak.read_entry(entry, out_stream)
                record = {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "source_pak": str(pak_path),
                    "source_pak_size": pak_path.stat().st_size,
                    "layer": layer,
                    "asset_path": entry.path,
                    "combined_hash": f"{entry.combined_hash:016X}",
                    "compressed_size": entry.compressed_size,
                    "decompressed_size": entry.decompressed_size,
                    "compression": entry.compression,
                    "resource_encryption": entry.encryption,
                    "pak_version": f"{pak.header.major}.{pak.header.minor}" if pak.header else None,
                    "pak_flags": pak.header.feature_flags if pak.header else None,
                    "output_path": str(target),
                    "output_size": target.stat().st_size,
                    "output_sha256": sha256_file(target),
                }
                manifest.write(json.dumps(record, ensure_ascii=False) + "\n")
                extracted += 1

    print(json.dumps({"selected_paths": len(known_paths), "pak_count": len(paks), "extracted": extracted, "manifest": str(manifest_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
