import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from service.tool_service import ToolLoadError, load_and_execute_project_tool


class ToolPathValidationTest(unittest.TestCase):
    def test_rejects_project_path_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tools_dir = root / "tools"
            tools_dir.mkdir()
            (root / "escape.py").write_text("VALUE = 1\n", encoding="utf-8")

            with (
                patch("service.tool_service.settings.tools_dir", str(tools_dir)),
                self.assertRaisesRegex(ValueError, "项目名称不合法"),
            ):
                load_and_execute_project_tool("..", "escape")

    def test_rejects_invalid_tool_name_before_log_path_creation(self):
        with self.assertRaisesRegex(ValueError, "工具名称不合法"):
            load_and_execute_project_tool("demo", "../escape")

    def test_rejects_legacy_top_level_tool_without_main(self):
        with tempfile.TemporaryDirectory() as directory:
            tools_dir = Path(directory) / "tools"
            project_dir = tools_dir / "demo"
            project_dir.mkdir(parents=True)
            (project_dir / "legacy.py").write_text(
                "print('legacy')\n", encoding="utf-8"
            )

            with (
                patch("service.tool_service.settings.tools_dir", str(tools_dir)),
                self.assertRaisesRegex(ToolLoadError, r"必须定义顶层 main\(\)"),
            ):
                load_and_execute_project_tool("demo", "legacy")


if __name__ == "__main__":
    unittest.main()
