"""Distribution and generated-document regressions for the standalone website."""

import hashlib
import json
import re
import shutil
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from scripts.build_website_docs import load_docs, render_page, website_links

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "website"


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"img", "script", "link"}:
            value = attrs.get("src") or attrs.get("href")
            if value and not value.startswith(("https:", "http:", "data:")):
                self.assets.append(urlsplit(value).path)


class WebsiteTest(unittest.TestCase):
    def test_standalone_site_assets_exist(self):
        parser = AssetParser()
        parser.feed((SITE / "index.html").read_text())
        for asset in parser.assets:
            with self.subTest(asset=asset):
                self.assertTrue((SITE / asset).is_file())
        self.assertEqual(
            (SITE / "LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes()
        )

    def test_available_browser_demos_have_gifs_and_posters(self):
        for stage in ("create", "preview", "publish", "use"):
            for language in ("zh", "en"):
                with self.subTest(stage=stage, language=language):
                    gif = SITE / "assets/demos" / f"{stage}-{language}.gif"
                    poster = gif.with_suffix(".webp")
                    self.assertIn(gif.read_bytes()[:6], (b"GIF89a", b"GIF87a"))
                    self.assertEqual(poster.read_bytes()[8:12], b"WEBP")
                    self.assertLess(gif.stat().st_size, 2_000_000)

    def test_generated_desktop_scenes_are_disclosed(self):
        homepage = (SITE / "index.html").read_text()
        script = (SITE / "site.js").read_text()
        self.assertNotRegex(homepage + script, r"\bCLI\b")
        self.assertNotIn("录屏待补充", homepage + script)
        self.assertIn("AI 生成流程示意", homepage)
        self.assertIn("AI-generated workflow illustration", script)
        self.assertNotIn("非真实录屏", homepage + script)
        for name in ("create", "publish"):
            self.assertTrue((SITE / "assets/illustrations" / f"{name}.png").is_file())

    def test_documentation_is_regenerated(self):
        self.assertEqual((SITE / "docs.html").read_text(), render_page(load_docs()))

    def test_relative_document_links_stay_in_static_viewer(self):
        self.assertEqual(
            website_links("[Demo](demo.md)", Path("README.md")), "[Demo](#demo)"
        )
        self.assertEqual(
            website_links("[Home](../README.md)", Path("plans/example.md")),
            "[Home](#README)",
        )
        self.assertEqual(
            website_links("[External](https://example.com)", Path("README.md")),
            "[External](https://example.com)",
        )

    def test_recording_source_matches_provenance(self):
        provenance = json.loads((SITE / "demos/provenance.json").read_text())
        source = (SITE / "demos/order_workspace.py").read_bytes()
        self.assertEqual(
            hashlib.sha256(source).hexdigest(), provenance["source_sha256"]
        )
        self.assertTrue(provenance["publish"]["success"])
        self.assertTrue(provenance["status"]["published"])

    @unittest.skipUnless(
        shutil.which("node"), "Node is optional for static website checks"
    )
    def test_generated_markdown_renderer_handles_links_lists_and_code(self):
        html = (SITE / "docs.html").read_text()
        script = re.findall(r"<script>([\s\S]*?)</script>", html)[-1]
        pure = script[
            script.index("      const escapeHtml") : script.index(
                "      function showDoc"
            )
        ]
        markdown = "## Heading\n\n[Demo](#demo)\n\n**Bold**\n\n1. First\n2. Second\n\n```python\nprint('<demo>')\n```"
        result = subprocess.run(
            [
                "node",
                "-e",
                pure + "\nconsole.log(renderMarkdown(" + json.dumps(markdown) + "));",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        for expected in (
            "<h2>Heading</h2>",
            '<a href="#demo">Demo</a>',
            "<strong>Bold</strong>",
            "<li>First</li>",
            "&lt;demo&gt;",
        ):
            self.assertIn(expected, result.stdout)
