"""Regression checks for distributed skill scripts and query state behavior."""

import ast
import asyncio
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import traceback
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SKILL = Path(__file__).resolve().parents[1] / "plugins/nicetool/skills/nicetool"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_module("validate_tool", SKILL / "scripts/validate-tool.py")
        cls.source = (SKILL / "references/simple-tool.py").read_text()

    def test_both_templates_pass_without_importing(self):
        for name in ("simple-tool.py", "query-tool.py"):
            self.assertEqual(
                self.validator.validate_source(
                    (SKILL / "references" / name).read_text()
                ),
                [],
            )

    def test_invalid_contracts_fail(self):
        cases = {
            "syntax": "def main(:",
            "missing_metadata": self.source.replace("project: nicetool", "project:"),
            "bad_tags": self.source.replace(
                "tags: 表单, 异步任务, 结果展示", "tags: one"
            ),
            "decorator": self.source.replace("def main()", "@wrapper\ndef main()"),
            "missing_main": self.source.replace("def main()", "def other()"),
            "missing_guard": self.source.split("if __name__")[0],
            "empty_guard": self.source.split("if __name__")[0]
            + 'if __name__ == "__main__":\n    pass\n',
        }
        for name, source in cases.items():
            with self.subTest(name=name):
                self.assertTrue(self.validator.validate_source(source))

    def test_validation_does_not_execute_source(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "must-not-exist"
            source = Path(directory) / "tool.py"
            source.write_text(
                self.source + f'\nopen({str(marker)!r}, "w").write("executed")\n'
            )
            result = subprocess.run(
                [sys.executable, str(SKILL / "scripts/validate-tool.py"), str(source)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(marker.exists())

    def test_entrypoint_must_run_when_called_without_arguments(self):
        for signature in ("required", "required, /", "*, required"):
            with self.subTest(signature=signature):
                source = self.source.replace("def main()", f"def main({signature})")
                self.assertTrue(self.validator.validate_source(source))
        for body in ("yield 1", "yield from ()"):
            source = self.source.replace(
                "def main() -> None:", f"def main():\n    {body}"
            )
            self.assertTrue(self.validator.validate_source(source))
        async_generator = self.source.replace(
            "def main() -> None:", "async def main():\n    yield 1"
        )
        self.assertTrue(self.validator.validate_source(async_generator))

    def test_optional_arguments_and_nested_generators_are_allowed(self):
        for signature in ("value=None", "*, value=None", "*args, **kwargs"):
            source = self.source.replace("def main()", f"def main({signature})")
            self.assertEqual(self.validator.validate_source(source), [])
        source = self.source.replace(
            "def main() -> None:", "def main():\n    def rows():\n        yield 1"
        )
        self.assertEqual(self.validator.validate_source(source), [])


class VariableReferenceTest(unittest.TestCase):
    def test_conversion_example_does_not_disclose_invalid_value(self):
        from loguru import logger

        reference = (SKILL / "references/variables.md").read_text()
        example = next(
            block.split("```", 1)[0]
            for block in reference.split("```python\n")[1:]
            if "def get_positive_int" in block
        )
        # 执行实际文档函数，代理和日志注入本地替身，不导入平台或访问数据库。
        tree = ast.parse(example)
        tree.body = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        secret = "EVAL_VALUE_SHOULD_NOT_BE_LOGGED"
        values = {"REQUEST_TIMEOUT": secret}
        namespace = {"variables": values, "logger": logger}
        exec(compile(tree, "<variable-reference>", "exec"), namespace)  # noqa: S102 — 仅执行本测试生成的受控代码，验证生成结果。
        output = io.StringIO()
        sink = logger.add(output, diagnose=True)
        try:
            try:
                namespace["get_positive_int"]("REQUEST_TIMEOUT", "30")
            except ValueError:
                formatted = traceback.format_exc()
            else:
                self.fail("Invalid integer was accepted")
        finally:
            logger.remove(sink)
        self.assertNotIn(secret, output.getvalue() + formatted)
        self.assertIn("REQUEST_TIMEOUT", output.getvalue())
        values.clear()
        self.assertEqual(namespace["get_positive_int"]("REQUEST_TIMEOUT", "30"), 30)
        values["REQUEST_TIMEOUT"] = "0"
        with self.assertRaises(ValueError):
            namespace["get_positive_int"]("REQUEST_TIMEOUT", "30")


class Control:
    def __init__(self, value=None):
        self.value = value
        self.enabled = True
        self.visible = True
        self.rows = []
        self.text = ""

    def disable(self):
        self.enabled = False

    def enable(self):
        self.enabled = True

    def set_enabled(self, enabled):
        self.enabled = enabled

    def set_value(self, value):
        self.value = value

    def set_text(self, text):
        self.text = text

    def update(self):
        pass


class QueryStateTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.module = load_module("query_template", SKILL / "references/query-tool.py")
        self.tool = self.make_tool()

    def make_tool(self):
        tool = self.module.DataQueryTool()
        for name in (
            "keyword_input",
            "status_select",
            "search_button",
            "reset_button",
            "previous_button",
            "next_button",
            "loading_row",
            "empty_label",
            "error_label",
            "table",
            "pagination_row",
            "pagination_label",
        ):
            setattr(tool, name, Control())
        tool.keyword_input.value = "A"
        tool.status_select.value = "正常"
        return tool

    async def test_pagination_uses_submitted_filters_until_next_search(self):
        async def query(*args):
            return self.module.QueryResult([{"id": 1}], 30)

        with patch.object(self.module.run, "io_bound", side_effect=query) as worker:
            await self.tool.submit_search()
            self.tool.keyword_input.value = "B"
            await self.tool.change_page(1)
            self.assertEqual(worker.call_args.args[1:], ("A", "正常", 2, 10))
            with patch.object(self.module.ui, "notify"):
                self.tool.reset_filters()
            self.assertEqual(self.tool.current_page, 2)
            await self.tool.change_page(1)
            self.assertEqual(worker.call_args.args[1:], ("A", "正常", 3, 10))
            await self.tool.submit_search()
            self.assertEqual(worker.call_args.args[1:], ("", None, 1, 10))

    async def test_page_correction_reuses_snapshot_and_latest_total(self):
        self.tool.current_page = 3
        self.tool.submitted_filters = ("A", "正常")

        async def query(_function, keyword, status, page, size):
            self.tool.keyword_input.value = "B"
            if page == 3:
                return self.module.QueryResult([], 15)
            return self.module.QueryResult([{"id": 11}], 12)

        with patch.object(self.module.run, "io_bound", side_effect=query) as worker:
            await self.tool.search(reset_page=False)
            self.assertEqual(worker.call_args.args[1:], ("A", "正常", 2, 10))
            self.assertEqual(self.tool.total_count, 12)
            self.assertEqual(self.tool.current_page, 2)
            self.assertTrue(self.tool.table.visible)

    async def test_failure_restores_controls_and_allows_retry(self):
        with (
            patch.object(
                self.module.run, "io_bound", side_effect=RuntimeError("test failure")
            ),
            patch.object(self.module.logger, "exception"),
        ):
            await self.tool.submit_search()
        self.assertFalse(self.tool.busy)
        self.assertTrue(self.tool.search_button.enabled)
        self.assertTrue(self.tool.reset_button.enabled)
        self.assertTrue(self.tool.error_label.visible)
        with patch.object(
            self.module.run, "io_bound", return_value=self.module.QueryResult([], 0)
        ):
            await self.tool.submit_search()
        self.assertTrue(self.tool.empty_label.visible)
        self.assertFalse(self.tool.error_label.visible)

    async def test_overlapping_submission_is_ignored_and_instances_are_private(self):
        started, finish = asyncio.Event(), asyncio.Event()

        async def query(*args):
            started.set()
            await finish.wait()
            return self.module.QueryResult([{"id": 1}], 1)

        other = self.make_tool()
        with patch.object(self.module.run, "io_bound", side_effect=query) as worker:
            pending = asyncio.create_task(self.tool.submit_search())
            await started.wait()
            try:
                self.tool.keyword_input.value = "B"
                await self.tool.submit_search()
                self.assertEqual(worker.call_count, 1)
                self.assertFalse(other.busy)
                self.assertEqual(other.submitted_filters, ("", None))
            finally:
                finish.set()
                await pending
        self.assertEqual(other.rows, [])


class InstalledCliTest(unittest.TestCase):
    def test_create_from_arbitrary_installation_and_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for location in ("plugin cache/nicetool", "home/.agents/skills/nicetool"):
                installed = base / location
                shutil.copytree(
                    SKILL / "scripts",
                    installed / "scripts",
                    ignore=shutil.ignore_patterns("__pycache__"),
                )
                workspace = base / ("workspace-" + str(len(location)))
                workspace.mkdir()
                source = workspace / "draft.py"
                source.write_text((SKILL / "references/simple-tool.py").read_text())
                result = subprocess.run(
                    [
                        sys.executable,
                        str(installed / "scripts/tool-cli.py"),
                        "--json",
                        "create",
                        "demo",
                        "example",
                        "--file",
                        str(source),
                    ],
                    cwd=workspace,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue(json.loads(result.stdout)["success"])
                self.assertEqual(
                    (workspace / "tools/demo/example.py").read_text(),
                    source.read_text(),
                )
                self.assertFalse((installed / "tools").exists())


class PreviewLogSnapshotTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clients = [
            load_module("log_cli_" + str(index), SKILL / "scripts" / filename)
            for index, filename in enumerate(("tool-cli.py",))
        ]

    def invoke(self, client, status=200, content="", **overrides):
        values = {
            "server": "https://example.invalid/app",
            "target": "demo",
            "name": "orders",
            "lines": 3,
            "max_chars": 20,
            "grep": None,
            "follow": False,
            "json": True,
        }
        values.update(overrides)
        output = io.StringIO()
        with (
            patch.object(
                client, "make_raw_request", return_value=(status, content)
            ) as raw,
            patch.object(client, "make_request", return_value={"tools": []}) as request,
            redirect_stdout(output),
        ):
            try:
                client.cmd_prelog(SimpleNamespace(**values))
                exit_code = 0
            except SystemExit as exc:
                exit_code = exc.code
        return json.loads(output.getvalue()), exit_code, raw, request

    def test_fixed_snapshot_is_bounded_and_retains_latest_error(self):
        for client in self.clients:
            with self.subTest(client=client.__name__):
                payload, code, raw, request = self.invoke(
                    client, content="old\n" + "a" * 100 + "\nlatest error\n"
                )
                self.assertEqual(code, 0)
                self.assertTrue(payload["truncated"])
                self.assertLessEqual(len(payload["content"]), 20)
                self.assertTrue(payload["content"].endswith("latest error\n"))
                raw.assert_called_once_with(
                    "https://example.invalid/app/api/tools/preview/log/fixed/demo/orders?lines=3"
                )
                request.assert_not_called()

    def test_token_empty_log_and_literal_filter(self):
        for client in self.clients:
            payload, code, raw, _ = self.invoke(client, name=None, target="token")
            self.assertEqual(code, 0)
            self.assertEqual(payload["content"], "")
            self.assertFalse(payload["truncated"])
            raw.assert_called_once_with(
                "https://example.invalid/app/api/tools/preview/log/token?lines=3"
            )
            payload, _, _, _ = self.invoke(
                client, content="old\nERROR bad\ninfo\n", grep="error"
            )
            self.assertEqual(payload["content"], "ERROR bad\n")

    def test_failures_are_structured_without_raw_error_body(self):
        for client in self.clients:
            for status in (0, 401, 403, 404, 500):
                with self.subTest(client=client.__name__, status=status):
                    payload, code, raw, _ = self.invoke(
                        client, status=status, content="private connection details"
                    )
                    self.assertEqual(code, 1)
                    self.assertFalse(payload["success"])
                    self.assertEqual(payload["status"], status)
                    self.assertNotIn("private", json.dumps(payload))
                    raw.assert_called_once()

    def test_invalid_or_follow_requests_do_not_contact_server(self):
        for client in self.clients:
            for options in (
                {"follow": True},
                {"lines": 0},
                {"lines": 10001},
                {"max_chars": 0},
                {"target": None},
            ):
                payload, code, raw, request = self.invoke(client, **options)
                self.assertEqual(code, 1)
                self.assertEqual(payload["code"], "invalid_arguments")
                raw.assert_not_called()
                request.assert_not_called()

    def test_preview_listing_is_json(self):
        for client in self.clients:
            payload, code, raw, request = self.invoke(client, target=None, name=None)
            self.assertEqual(code, 0)
            self.assertEqual(payload, {"success": True, "tools": []})
            request.assert_called_once_with(
                "https://example.invalid/app/api/tools/preview/list"
            )
            raw.assert_not_called()
