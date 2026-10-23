"""上线前简化后的发布、名称和下载契约。"""

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.auth.actor import system_actor
from core.database import DatabaseManager
from core.tool_identity import InvalidToolIdentity, validate_tool_identity
from public.api.tool_api import ToolMetaResponse, router
from service import tool_lifecycle_service as lifecycle
from service import tool_manage_service
from service.tool_service import load_and_execute_project_tool
from service.tool_storage import ToolStorage


class CleanupContractsTest(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_publish_requires_source_body(self):
        with patch("service.tool_lifecycle_service.get_tool_storage") as storage:
            for body in (None, {}, {"content": None}, {"content": ""}):
                with self.subTest(body=body):
                    response = self.client.post(
                        "/api/tools/demo/hello/publish", json=body
                    )
                    self.assertEqual(response.status_code, 422)
            storage.assert_not_called()

    def test_invalid_names_never_reach_storage_or_filesystem(self):
        actor = system_actor("test")
        for project, name in (
            ("Demo", "hello"),
            ("demo", "hello.py"),
            ("demo", "hello world"),
            ("..", "hello"),
            ("demo", ""),
            ("demo", "x" * 198),
        ):
            with (
                self.subTest(project=project, name=name),
                patch("service.tool_lifecycle_service.get_tool_storage") as storage,
            ):
                for operation in (
                    lambda project=project, name=name: lifecycle.publish_tool(
                        actor, project, name, "def main(): pass"
                    ),
                    lambda project=project, name=name: lifecycle.delete_tool(
                        actor, project, name
                    ),
                    lambda project=project, name=name: lifecycle.get_tool_state(
                        actor, project, name
                    ),
                    lambda project=project, name=name: lifecycle.rollback_tool(
                        actor, project, name, "v1"
                    ),
                    lambda project=project, name=name: lifecycle.restore_runtime_cache(
                        actor, project, name
                    ),
                    lambda project=project, name=name: lifecycle.list_tool_events(
                        actor, project, name
                    ),
                ):
                    self.assertEqual(operation().code, "invalid_identity")
                storage.assert_not_called()
                with self.assertRaises(InvalidToolIdentity):
                    tool_manage_service.get_tool(project, name)
                with self.assertRaises(InvalidToolIdentity):
                    tool_manage_service.delete_tool(project, name)

    def test_api_rejects_names_instead_of_normalizing(self):
        with (
            patch("core.auth.service.auth_service.is_enabled", return_value=False),
            patch("service.tool_lifecycle_service.get_tool_storage") as storage,
        ):
            response = self.client.post(
                "/api/tools/demo/Hello.py/publish", json={"content": "def main(): pass"}
            )
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json()["code"], "invalid_identity")
            self.assertEqual(
                self.client.get("/api/tools/demo/Hello.py").status_code, 422
            )
            self.assertEqual(
                self.client.get("/api/tools?project=Demo").status_code, 422
            )
            storage.assert_not_called()

    def test_upload_failure_does_not_restore_cache_or_report_success(self):
        with (
            patch("service.tool_lifecycle_service.get_tool_storage") as factory,
            patch("service.tool_lifecycle_service.record_lifecycle_event") as event,
        ):
            factory.return_value.save_current.return_value = {
                "success": False,
                "error": "write failed",
            }
            result = lifecycle.publish_tool(
                system_actor("test"), "demo", "hello", "def main(): pass"
            )
            self.assertEqual(result.code, "publish_failed")
            factory.return_value.restore_current_to_local.assert_not_called()
            self.assertFalse(event.call_args.kwargs["success"])

    def test_names_accept_exact_limits_without_rewriting(self):
        pair = ("a" * 100, "b" * 197)
        self.assertEqual(validate_tool_identity(*pair), pair)
        with self.assertRaises(InvalidToolIdentity):
            validate_tool_identity("a" * 101, "hello")

    def test_storage_rejects_filename_alias_before_database_access(self):
        with patch("service.tool_storage.db_manager") as database:
            storage = ToolStorage()
            for operation in (
                lambda: storage.save_current("demo", "hello.py", "def main(): pass"),
                lambda: storage.load_current("demo", "hello.py"),
                lambda: storage.delete_tool("demo", "hello.py"),
                lambda: storage.restore_current_to_local("demo", "hello.py"),
            ):
                with self.assertRaises(InvalidToolIdentity):
                    operation()
            database.session_scope.assert_not_called()

    def test_tool_metadata_has_no_revision_field(self):
        self.assertNotIn("revision", ToolMetaResponse.model_fields)

    def test_cache_miss_still_restores_from_database(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("service.tool_manage_service.settings.tools_dir", directory),
            patch("service.tool_manage_service.get_tool_storage") as factory,
        ):

            def restore(project, name):
                path = Path(directory) / project / f"{name}.py"
                path.parent.mkdir()
                path.write_text('"""name: Hello"""\ndef main(): pass\n')
                return str(path)

            factory.return_value.restore_current_to_local.side_effect = restore
            result = tool_manage_service.get_tool("demo", "hello", include_content=True)
            self.assertEqual(result["meta"]["title"], "Hello")
            self.assertNotIn("revision", result["meta"])
            factory.return_value.restore_current_to_local.assert_called_once_with(
                "demo", "hello"
            )

    def test_uninitialized_database_raises_runtime_error(self):
        manager = DatabaseManager.__new__(DatabaseManager)
        manager.engine = None
        with self.assertRaises(RuntimeError):
            manager.get_session()
        with self.assertRaises(RuntimeError):
            manager.create_tables()

    def test_missing_tool_raises_file_not_found(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("service.tool_service.settings.tools_dir", directory),
            self.assertRaises(FileNotFoundError),
        ):
            load_and_execute_project_tool("demo", "missing")


class CliCleanupContractsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        script = (
            Path(__file__).resolve().parents[1]
            / "plugins/nicetool/skills/nicetool/scripts/tool-cli.py"
        )
        spec = importlib.util.spec_from_file_location("cleanup_cli", script)
        cls.cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.cli)

    def test_get_writes_source_without_auxiliary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "hello.py"
            args = SimpleNamespace(
                server="http://example.com",
                project="demo",
                name="hello",
                output=str(output),
                json=True,
            )
            stdout = io.StringIO()
            with (
                patch.object(
                    self.cli,
                    "make_request",
                    return_value={"meta": {}, "content": "def main(): pass"},
                ),
                redirect_stdout(stdout),
            ):
                self.cli.cmd_get(args)
            self.assertEqual(list(Path(directory).iterdir()), [output])
            self.assertEqual(
                json.loads(stdout.getvalue()), {"success": True, "output": str(output)}
            )

    def test_create_rejects_invalid_identity_before_reading_or_writing(self):
        args = SimpleNamespace(project="../escape", name="hello")
        with (
            patch.object(self.cli, "_read_tool_content") as read,
            self.assertRaises(ValueError),
        ):
            self.cli.cmd_create(args)
        read.assert_not_called()

    def test_connection_errors_have_explicit_type(self):
        with (
            patch.object(self.cli, "urlopen", side_effect=self.cli.URLError("offline")),
            self.assertRaises(ConnectionError),
        ):
            self.cli.make_request("http://example.com")
