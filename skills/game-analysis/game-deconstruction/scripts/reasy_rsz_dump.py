#!/usr/bin/env python3
"""Dump RE Engine RSZ instance types and fields through an external REasy source tree."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reasy-source", required=True, type=Path)
    parser.add_argument("--rsz-dump", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--game-version", required=True, help="Target RE Engine game identifier supported by the selected registry")
    parser.add_argument("--max-depth", type=int, default=12)
    parser.add_argument("--allow-registry-mismatch", action="store_true")
    return parser.parse_args()


def convert(value: Any, depth: int, max_depth: int, seen: set[int]) -> Any:
    if depth > max_depth:
        return "<max-depth>"
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, bytes):
        return {"type": "bytes", "size": len(value), "hex": value[:64].hex()}
    if isinstance(value, memoryview):
        raw = bytes(value)
        return {"type": "memoryview", "size": len(raw), "hex": raw[:64].hex()}

    object_id = id(value)
    if object_id in seen:
        return "<cycle>"
    seen.add(object_id)
    try:
        if isinstance(value, dict):
            return {str(key): convert(item, depth + 1, max_depth, seen) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [convert(item, depth + 1, max_depth, seen) for item in value]
        if hasattr(value, "__dict__"):
            payload = {
                key: convert(item, depth + 1, max_depth, seen)
                for key, item in vars(value).items()
                if not key.startswith("_")
            }
            payload["$class"] = value.__class__.__name__
            return payload
        return str(value)
    finally:
        seen.discard(object_id)


def main() -> int:
    args = parse_args()
    source = args.reasy_source.resolve()
    if not (source / "file_handlers" / "rsz" / "rsz_file.py").is_file():
        raise SystemExit("--reasy-source 不是可识别的 REasy 源码目录")
    if not args.rsz_dump.is_file() or not args.input.is_file():
        raise SystemExit("RSZ dump 或输入文件不存在")

    sys.path.insert(0, str(source))
    from file_handlers.rsz.rsz_file import RszFile, TypeRegistryValidationError
    from utils.type_registry import TypeRegistry

    registry = TypeRegistry(str(args.rsz_dump))
    def new_rsz() -> Any:
        parsed = RszFile()
        parsed.type_registry = registry
        parsed.game_version = args.game_version
        parsed.filepath = str(args.input)
        return parsed

    data = args.input.read_bytes()
    rsz = new_rsz()
    validation_issues = []
    try:
        rsz.read(data, validate_type_registry=True)
    except TypeRegistryValidationError as exc:
        validation_issues = list(exc.issues)
        if not args.allow_registry_mismatch:
            preview = "; ".join(validation_issues[:5])
            raise SystemExit(f"RSZ 类型表验证失败：{preview}；确认后使用 --allow-registry-mismatch") from exc
        rsz = new_rsz()
        rsz.read(data, validate_type_registry=False)

    instances = []
    for index, info in enumerate(rsz.instance_infos):
        type_info = registry.get_type_info(info.type_id) or {}
        instances.append(
            {
                "instance_id": index,
                "type_id": f"0x{info.type_id:08X}",
                "type_name": type_info.get("name", "<unknown>"),
                "crc": getattr(info, "crc", None),
                "fields": convert(rsz.parsed_elements.get(index, {}), 0, args.max_depth, set()),
            }
        )

    result = {
        "source": str(args.input.resolve()),
        "game_version": args.game_version,
        "kind": "USR" if rsz.is_usr else "PFB" if rsz.is_pfb else "SCN",
        "instance_count": len(instances),
        "registry_validation": "mismatch-allowed" if validation_issues else "passed",
        "registry_validation_issues": validation_issues,
        "resource_paths": [str(item) for item in getattr(rsz, "resource_infos", [])],
        "instances": instances,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output.resolve()), "instances": len(instances)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
