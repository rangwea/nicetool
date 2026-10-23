import tempfile
import unittest
from pathlib import Path

from service.preview_service import save_preview
from service.tool_runtime import (
    ToolEntryPointError,
    load_tool_entrypoint,
    validate_tool_entrypoint,
)


class ToolRuntimeTest(unittest.TestCase):
    def test_validates_sync_and_async_main(self):
        self.assertFalse(validate_tool_entrypoint("def main():\n    pass\n"))
        self.assertTrue(validate_tool_entrypoint("async def main():\n    pass\n"))

    def test_rejects_nested_or_missing_main(self):
        with self.assertRaises(ToolEntryPointError):
            validate_tool_entrypoint("if True:\n    def main():\n        pass\n")

    def test_loads_callable_main(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tool.py"
            path.write_text("def main():\n    return 42\n", encoding="utf-8")

            main, is_async = load_tool_entrypoint("runtime_test_tool", str(path))

            self.assertFalse(is_async)
            self.assertEqual(main(), 42)

    def test_preview_rejects_content_without_main(self):
        result = save_preview(
            preview_key="missing-main-test",
            content="print('legacy')\n",
            preview_type="temporary",
            url="/client/tool/missing-main-test",
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["code"], "missing_main")
        self.assertEqual(result["next_action"], "add_main")


if __name__ == "__main__":
    unittest.main()
