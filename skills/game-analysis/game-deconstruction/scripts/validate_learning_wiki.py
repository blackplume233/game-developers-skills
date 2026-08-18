#!/usr/bin/env python3
"""Validate the publication boundary of a game-deconstruction learning Wiki."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_FORBIDDEN_MARKERS = (
    "## 闭卷自测",
    "费曼理解测试",
    "### 答案要点",
    "独立费曼审查",
    "独立费曼验证",
    "SubAgent",
    "未独立验证",
)
DEFAULT_INTERNAL_PARTS = {".internal", "review", "reviews", "audit", "audits"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--content-root",
        type=Path,
        help="Base directory for page paths in the manifest; defaults to project root.",
    )
    parser.add_argument(
        "--forbidden-marker",
        action="append",
        default=[],
        help="Additional reader-facing marker to reject; repeat as needed.",
    )
    parser.add_argument(
        "--public-root",
        type=Path,
        action="append",
        default=[],
        help="Additional built/search/public directory to scan; repeat as needed.",
    )
    parser.add_argument(
        "--web-root",
        type=Path,
        help="Public Web root containing the HTML pages and shared design assets.",
    )
    parser.add_argument(
        "--design-manifest",
        type=Path,
        help="Multi-page delivery design-system manifest; requires --web-root.",
    )
    return parser.parse_args()


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def iter_pages(manifest: dict) -> list[str]:
    pages: list[str] = []
    for group in manifest.get("groups", []):
        for page in group.get("pages", []):
            page_path = page.get("path")
            if isinstance(page_path, str) and page_path.strip():
                pages.append(page_path.replace("\\", "/"))
    return pages


def resolve_public_file(relative: object, web_root: Path, label: str, errors: list[str]) -> Path | None:
    if not isinstance(relative, str) or not relative.strip():
        errors.append(f"{label}路径为空")
        return None
    relative_path = Path(relative.replace("\\", "/"))
    if relative_path.is_absolute() or ".." in relative_path.parts:
        errors.append(f"{label}路径越界: {relative}")
        return None
    candidate = (web_root / relative_path).resolve()
    if not is_within(candidate, web_root):
        errors.append(f"{label}解析后越界: {relative}")
        return None
    if not candidate.is_file():
        errors.append(f"{label}不存在: {relative}")
        return None
    return candidate


def validate_design_system(
    design_manifest: dict,
    web_root: Path,
    errors: list[str],
) -> dict[str, int | str]:
    page_entries = design_manifest.get("pages", [])
    if not isinstance(page_entries, list):
        errors.append("设计系统清单 pages 必须是数组")
        page_entries = []

    page_paths: list[str] = []
    page_files: dict[str, Path] = {}
    page_roles: dict[str, str] = {}
    for entry in page_entries:
        if not isinstance(entry, dict):
            errors.append("设计系统清单包含非对象 page")
            continue
        path = entry.get("path")
        role = entry.get("role")
        if not isinstance(role, str) or not role.strip():
            errors.append(f"设计系统页面缺少 role: {path!r}")
        candidate = resolve_public_file(path, web_root, "设计系统页面", errors)
        if candidate is not None and isinstance(path, str):
            normalized = path.replace("\\", "/")
            if candidate.suffix.lower() not in {".htm", ".html"}:
                errors.append(f"设计系统页面不是 HTML: {normalized}")
            page_paths.append(normalized)
            page_files[normalized] = candidate
            if isinstance(role, str):
                page_roles[normalized] = role.strip()

    if len(page_paths) < 2:
        errors.append("多页面设计系统清单至少需要两个 HTML 入口")
    if len(page_paths) != len(set(page_paths)):
        errors.append("设计系统清单包含重复页面")

    visual_source = str(design_manifest.get("visual_source", "")).replace("\\", "/")
    if visual_source not in page_paths:
        errors.append("视觉真源不在设计系统页面清单中")
    elif page_roles.get(visual_source) != "book":
        errors.append("视觉真源页面的 role 必须是 book")

    shared_assets = design_manifest.get("shared_assets", {})
    if not isinstance(shared_assets, dict):
        errors.append("设计系统清单 shared_assets 必须是对象")
        shared_assets = {}
    tokens = shared_assets.get("tokens")
    icons = shared_assets.get("icons")
    token_file = resolve_public_file(tokens, web_root, "共享设计令牌", errors)
    icon_file = resolve_public_file(icons, web_root, "共享SVG精灵", errors)
    if token_file is not None and token_file.suffix.lower() != ".css":
        errors.append("共享设计令牌必须是 CSS 文件")
    if icon_file is not None and icon_file.suffix.lower() != ".svg":
        errors.append("共享图标资源必须是 SVG 文件")

    for page_path, page_file in page_files.items():
        try:
            html = page_file.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            errors.append(f"设计系统页面无法按 UTF-8 读取: {page_path}: {error}")
            continue
        if isinstance(tokens, str) and tokens not in html:
            errors.append(f"页面未引用共享设计令牌 {tokens!r}: {page_path}")
        if isinstance(icons, str) and icons not in html:
            errors.append(f"页面未引用共享SVG精灵 {icons!r}: {page_path}")

    evidence_surfaces = design_manifest.get("evidence_surfaces", [])
    if not isinstance(evidence_surfaces, list):
        errors.append("设计系统清单 evidence_surfaces 必须是数组")
        evidence_surfaces = []
    for surface in evidence_surfaces:
        if not isinstance(surface, dict):
            errors.append("设计系统清单包含非对象 evidence_surface")
            continue
        surface_page = str(surface.get("page", "")).replace("\\", "/")
        selectors = surface.get("selectors", [])
        if surface_page not in page_paths:
            errors.append(f"证据面板所属页面未登记: {surface_page!r}")
        if not isinstance(selectors, list) or not selectors or not all(
            isinstance(selector, str) and selector.strip() for selector in selectors
        ):
            errors.append(f"证据面板缺少有效 selectors: {surface_page!r}")
        if surface.get("mode") not in {"dark", "light", "dense"}:
            errors.append(f"证据面板 mode 必须是 dark、light 或 dense: {surface_page!r}")
        if not isinstance(surface.get("purpose"), str) or not surface["purpose"].strip():
            errors.append(f"证据面板缺少 purpose: {surface_page!r}")

    viewports = design_manifest.get("responsive_viewports", [])
    valid_viewports = sorted({value for value in viewports if isinstance(value, int) and value > 0}) \
        if isinstance(viewports, list) else []
    if len(valid_viewports) < 3 or valid_viewports[0] > 700 or valid_viewports[-1] < 1000:
        errors.append("响应式回归至少登记三个视口，并覆盖窄屏与宽屏")

    return {
        "design_pages": len(page_paths),
        "evidence_surfaces": len(evidence_surfaces),
        "responsive_viewports": len(valid_viewports),
        "tokens_present": int(token_file is not None),
        "icons_present": int(icon_file is not None),
        "visual_source": visual_source,
    }


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    content_root = (args.content_root or args.project_root).resolve()
    manifest_path = args.manifest.resolve()
    errors: list[str] = []
    design_result: dict[str, int | str] = {}

    if not is_within(content_root, root):
        errors.append("Wiki 内容根目录不在 Project 根目录内")

    if not is_within(manifest_path, root):
        errors.append("Wiki 清单不在 Project 根目录内")
        manifest: dict = {}
    elif not manifest_path.is_file():
        errors.append(f"Wiki 清单不存在: {manifest_path}")
        manifest = {}
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"Wiki 清单无法读取: {error}")
            manifest = {}

    pages = iter_pages(manifest)
    if not pages:
        errors.append("Wiki 清单没有发布页面")
    if len(pages) != len(set(pages)):
        errors.append("Wiki 清单包含重复页面路径")

    default_page = str(manifest.get("default_page", "")).replace("\\", "/")
    if default_page not in pages:
        errors.append("默认页不在发布清单中")

    forbidden = DEFAULT_FORBIDDEN_MARKERS + tuple(args.forbidden_marker)
    checked_pages = 0
    checked_artifacts = 0
    for relative in pages:
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            errors.append(f"发布页路径越界: {relative}")
            continue
        if DEFAULT_INTERNAL_PARTS.intersection(part.lower() for part in relative_path.parts):
            errors.append(f"内部目录出现在发布清单: {relative}")
            continue

        page_path = (content_root / relative_path).resolve()
        if not is_within(page_path, content_root):
            errors.append(f"发布页解析后越界: {relative}")
            continue
        if not page_path.is_file():
            errors.append(f"发布页不存在: {relative}")
            continue

        try:
            text = page_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            errors.append(f"发布页无法按 UTF-8 读取: {relative}: {error}")
            continue
        checked_pages += 1
        for marker in forbidden:
            if marker in text:
                errors.append(f"发布页包含内部或测试标记 {marker!r}: {relative}")

    text_suffixes = {".css", ".htm", ".html", ".js", ".json", ".md", ".svg", ".txt", ".xml"}
    scan_roots = list(args.public_root)
    if args.web_root:
        scan_roots.append(args.web_root)
    seen_scan_roots: set[Path] = set()
    for public_root_arg in scan_roots:
        public_root = public_root_arg.resolve()
        if public_root in seen_scan_roots:
            continue
        seen_scan_roots.add(public_root)
        if not is_within(public_root, root):
            errors.append(f"公开产物目录不在 Project 内: {public_root}")
            continue
        if not public_root.is_dir():
            errors.append(f"公开产物目录不存在: {public_root}")
            continue
        for artifact in sorted(path for path in public_root.rglob("*") if path.is_file()):
            relative_artifact = artifact.relative_to(root)
            if DEFAULT_INTERNAL_PARTS.intersection(part.lower() for part in relative_artifact.parts):
                errors.append(f"内部目录被复制进公开产物: {relative_artifact.as_posix()}")
                continue
            if artifact.suffix.lower() not in text_suffixes:
                continue
            try:
                text = artifact.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as error:
                errors.append(f"公开产物无法按 UTF-8 读取: {relative_artifact.as_posix()}: {error}")
                continue
            checked_artifacts += 1
            for marker in forbidden:
                if marker in text:
                    errors.append(
                        f"公开产物包含内部或测试标记 {marker!r}: {relative_artifact.as_posix()}"
                    )

    if bool(args.web_root) != bool(args.design_manifest):
        errors.append("--web-root 与 --design-manifest 必须同时提供")
    elif args.web_root and args.design_manifest:
        web_root = args.web_root.resolve()
        design_manifest_path = args.design_manifest.resolve()
        if not is_within(web_root, root):
            errors.append("公开 Web 根目录不在 Project 内")
        elif not web_root.is_dir():
            errors.append(f"公开 Web 根目录不存在: {web_root}")
        elif not is_within(design_manifest_path, web_root):
            errors.append("设计系统清单不在公开 Web 根目录内")
        elif not design_manifest_path.is_file():
            errors.append(f"设计系统清单不存在: {design_manifest_path}")
        else:
            try:
                design_manifest = json.loads(design_manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                errors.append(f"设计系统清单无法读取: {error}")
            else:
                design_result = validate_design_system(design_manifest, web_root, errors)

    result = {
        "status": "passed" if not errors else "failed",
        "project_root": str(root),
        "content_root": str(content_root),
        "manifest": str(manifest_path),
        "published_pages": len(pages),
        "checked_pages": checked_pages,
        "checked_public_artifacts": checked_artifacts,
        "default_page": default_page,
        "design_system": design_result,
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
