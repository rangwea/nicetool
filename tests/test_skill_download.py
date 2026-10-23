import tempfile
from io import BytesIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from zipfile import ZipFile

from fastapi import HTTPException

from core.settings import Settings
from public.skill_download import (
    SKILL_SOURCE,
    _build_skill_archive,
    download_nicetool_skill,
)


class NiceToolSkillDownloadTest(TestCase):
    def test_distribution_contains_validator_and_routed_references(self):
        with ZipFile(BytesIO(_build_skill_archive())) as archive:
            names = set(archive.namelist())
            for relative in (
                "scripts/validate-tool.py",
                "scripts/preview_log.py",
                "references/datasources.md",
                "references/design-scenes.md",
                "references/design-details.md",
            ):
                self.assertIn(f"nicetool/{relative}", names)
            self.assertFalse(any("__pycache__" in name for name in names))
            self.assertIn("nicetool/scripts/tool-cli.py", names)
            self.assertNotIn("nicetool/scripts/tool-cli-py2.py", names)

    def test_distribution_source_is_the_plugin_skill(self):
        self.assertEqual(
            SKILL_SOURCE.parts[-4:],
            ("plugins", "nicetool", "skills", "nicetool"),
        )

    def test_downloads_are_public_by_default(self):
        public_paths = Settings(_env_file=None).csv_list(
            Settings(_env_file=None).auth_public_paths
        )

        self.assertIn("/api/downloads", public_paths)
        self.assertIn("/api/init.sh", public_paths)
        self.assertIn("/api/install.sh", public_paths)

    def test_returns_complete_skill_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "nicetool"
            (source / "references").mkdir(parents=True)
            (source / "scripts").mkdir()
            (source / "__pycache__").mkdir()
            (source / "SKILL.md").write_text("---\nname: nicetool\n---\n")
            (source / "references" / "lifecycle.md").write_text("lifecycle")
            (source / "scripts" / "tool-cli.py").write_text("print('ok')")
            (source / "__pycache__" / "cache.pyc").write_bytes(b"cache")

            with patch("public.skill_download.SKILL_SOURCE", source):
                response = download_nicetool_skill()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.media_type, "application/zip")
        self.assertEqual(
            response.headers["content-disposition"],
            'attachment; filename="nicetool-skill.zip"',
        )
        self.assertEqual(response.headers["cache-control"], "no-store")

        with ZipFile(BytesIO(response.body)) as archive:
            self.assertEqual(
                set(archive.namelist()),
                {
                    "nicetool/SKILL.md",
                    "nicetool/references/lifecycle.md",
                    "nicetool/scripts/tool-cli.py",
                },
            )

    def test_missing_skill_returns_service_unavailable(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("public.skill_download.SKILL_SOURCE", Path(directory) / "missing"),
            self.assertRaises(HTTPException) as caught,
        ):
            download_nicetool_skill()

        self.assertEqual(caught.exception.status_code, 503)
