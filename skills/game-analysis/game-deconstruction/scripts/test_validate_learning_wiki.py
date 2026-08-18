#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_learning_wiki.py")


class LearningWikiValidationTests(unittest.TestCase):
    def make_project(self, page_text: str = "# 方案总览\n\n公开教学内容。") -> tuple[Path, tempfile.TemporaryDirectory]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        content = root / "analysis-project"
        (content / "docs").mkdir(parents=True)
        (content / "docs" / "README.md").write_text(page_text, encoding="utf-8")
        manifest = {
            "default_page": "docs/README.md",
            "groups": [{"title": "开始", "pages": [{"path": "docs/README.md"}]}],
        }
        (root / "wiki-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        return root, temporary

    def run_validator(self, root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--project-root",
                str(root),
                "--content-root",
                str(root / "analysis-project"),
                "--manifest",
                str(root / "wiki-manifest.json"),
                *extra,
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def add_design_system(self, root: Path, second_page_uses_tokens: bool = True) -> Path:
        web = root / "explorer"
        web.mkdir()
        (web / "design-system.css").write_text(":root { color-scheme: light; }", encoding="utf-8")
        (web / "icons.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>', encoding="utf-8")
        shared_head = '<link rel="stylesheet" href="design-system.css">'
        icon = '<svg><use href="icons.svg#icon-book"></use></svg>'
        (web / "map.html").write_text(shared_head + icon, encoding="utf-8")
        asset_head = shared_head if second_page_uses_tokens else ""
        (web / "index.html").write_text(asset_head + icon + '<pre class="code-view"></pre>', encoding="utf-8")
        design = {
            "schema_version": "1.0",
            "visual_source": "map.html",
            "pages": [
                {"path": "map.html", "role": "book"},
                {"path": "index.html", "role": "asset-learning"},
            ],
            "shared_assets": {"tokens": "design-system.css", "icons": "icons.svg"},
            "evidence_surfaces": [
                {
                    "page": "index.html",
                    "selectors": [".code-view"],
                    "mode": "dark",
                    "purpose": "机器证据阅读",
                }
            ],
            "responsive_viewports": [1440, 900, 620],
        }
        manifest = web / "delivery-design-system.json"
        manifest.write_text(json.dumps(design, ensure_ascii=False), encoding="utf-8")
        return manifest

    def test_valid_reader_surface_passes(self) -> None:
        root, temporary = self.make_project()
        with temporary:
            result = self.run_validator(root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "passed")

    def test_internal_review_page_is_rejected(self) -> None:
        root, temporary = self.make_project()
        with temporary:
            review = root / "analysis-project" / ".internal" / "reviews" / "review.md"
            review.parent.mkdir(parents=True)
            review.write_text("内部审查", encoding="utf-8")
            manifest = json.loads((root / "wiki-manifest.json").read_text(encoding="utf-8"))
            manifest["groups"][0]["pages"].append({"path": ".internal/reviews/review.md"})
            (root / "wiki-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertNotEqual(self.run_validator(root).returncode, 0)

    def test_review_marker_in_reader_page_is_rejected(self) -> None:
        root, temporary = self.make_project("# 总览\n\n独立费曼审查：通过。")
        with temporary:
            self.assertNotEqual(self.run_validator(root).returncode, 0)

    def test_review_marker_in_built_artifact_is_rejected(self) -> None:
        root, temporary = self.make_project()
        with temporary:
            public = root / "dist"
            public.mkdir()
            (public / "search-index.json").write_text('{"text":"SubAgent"}', encoding="utf-8")
            result = self.run_validator(root, "--public-root", str(public))
            self.assertNotEqual(result.returncode, 0)

    def test_shared_delivery_design_system_passes(self) -> None:
        root, temporary = self.make_project()
        with temporary:
            design_manifest = self.add_design_system(root)
            result = self.run_validator(
                root,
                "--web-root",
                str(root / "explorer"),
                "--design-manifest",
                str(design_manifest),
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["design_system"]["design_pages"], 2)
            self.assertEqual(payload["design_system"]["tokens_present"], 1)
            self.assertEqual(payload["design_system"]["icons_present"], 1)

    def test_page_without_shared_tokens_is_rejected(self) -> None:
        root, temporary = self.make_project()
        with temporary:
            design_manifest = self.add_design_system(root, second_page_uses_tokens=False)
            result = self.run_validator(
                root,
                "--web-root",
                str(root / "explorer"),
                "--design-manifest",
                str(design_manifest),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("页面未引用共享设计令牌", result.stdout)


if __name__ == "__main__":
    unittest.main()
