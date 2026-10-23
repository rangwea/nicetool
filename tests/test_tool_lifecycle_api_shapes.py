import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def _load_tool_cli_module():
    script_path = (
        Path(__file__).resolve().parents[1]
        / "plugins"
        / "nicetool"
        / "skills"
        / "nicetool"
        / "scripts"
        / "tool-cli.py"
    )
    spec = importlib.util.spec_from_file_location("nicetool_tool_cli", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_module_from_path(module_name: str, script_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ApiShapeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        module = import_module("service.tool_lifecycle_service")
        cls.lifecycle_error = staticmethod(module.lifecycle_error)
        cls.lifecycle_success = staticmethod(module.lifecycle_success)

    def test_lifecycle_success_to_dict_has_stable_fields(self):
        result = self.lifecycle_success(message="ok", data={"meta": {"name": "hello"}})

        payload = result.to_dict()

        self.assertTrue(payload["success"])
        self.assertEqual(payload["code"], "ok")
        self.assertEqual(payload["message"], "ok")
        self.assertEqual(payload["next_action"], "")
        self.assertEqual(payload["meta"]["name"], "hello")

    def test_lifecycle_error_to_dict_has_stable_fields(self):
        result = self.lifecycle_error(
            code="publish_failed",
            message="publish failed",
            next_action="inspect_error",
            data={"detail": "detail"},
        )

        payload = result.to_dict()

        self.assertFalse(payload["success"])
        self.assertEqual(payload["code"], "publish_failed")
        self.assertEqual(payload["message"], "publish failed")
        self.assertEqual(payload["next_action"], "inspect_error")
        self.assertEqual(payload["detail"], "detail")

    def test_lifecycle_success_reserved_fields_cannot_be_overwritten(self):
        result = self.lifecycle_success(
            message="ok",
            data={
                "success": False,
                "code": "bad",
                "message": "bad",
                "next_action": "bad",
                "meta": {"name": "hello"},
            },
        )

        payload = result.to_dict()

        self.assertTrue(payload["success"])
        self.assertEqual(payload["code"], "ok")
        self.assertEqual(payload["message"], "ok")
        self.assertEqual(payload["next_action"], "")
        self.assertEqual(payload["meta"]["name"], "hello")

    def test_lifecycle_error_reserved_fields_cannot_be_overwritten(self):
        result = self.lifecycle_error(
            code="publish_failed",
            message="publish failed",
            next_action="inspect_error",
            data={
                "success": True,
                "code": "ok",
                "message": "ok",
                "next_action": "",
                "detail": "detail",
            },
        )

        payload = result.to_dict()

        self.assertFalse(payload["success"])
        self.assertEqual(payload["code"], "publish_failed")
        self.assertEqual(payload["message"], "publish failed")
        self.assertEqual(payload["next_action"], "inspect_error")
        self.assertEqual(payload["detail"], "detail")


class ToolCliErrorNormalizationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool_cli = _load_tool_cli_module()

    def test_normalize_error_payload_uses_detail_as_message(self):
        payload = self.tool_cli.normalize_error_payload({"detail": "bad"})

        self.assertFalse(payload["success"])
        self.assertEqual(payload["code"], "request_failed")
        self.assertEqual(payload["message"], "bad")
        self.assertEqual(payload["next_action"], "inspect_error")

    def test_normalize_error_payload_preserves_data_but_not_reserved_overrides(self):
        payload = self.tool_cli.normalize_error_payload(
            {
                "success": True,
                "code": "publish_failed",
                "message": "wrong",
                "detail": "detail",
                "error": "error",
                "next_action": "inspect_error",
                "extra": "extra",
            }
        )

        self.assertFalse(payload["success"])
        self.assertEqual(payload["code"], "publish_failed")
        self.assertEqual(payload["message"], "wrong")
        self.assertEqual(payload["next_action"], "inspect_error")
        self.assertEqual(payload["extra"], "extra")
        self.assertNotIn("detail", payload)
        self.assertNotIn("error", payload)

    def test_publish_uses_project_name_endpoint(self):
        args = SimpleNamespace(
            server="http://localhost:8000",
            project="demo",
            name="chart",
            file=None,
            stdin=False,
            json=True,
        )
        output = io.StringIO()

        with (
            patch.object(
                self.tool_cli,
                "_read_publish_content",
                return_value="print('chart')\n",
            ),
            patch.object(
                self.tool_cli,
                "make_request",
                return_value={"success": True, "version": "v1"},
            ) as request_mock,
            redirect_stdout(output),
        ):
            self.tool_cli.cmd_publish(args)

        request_mock.assert_called_once_with(
            "http://localhost:8000/api/tools/demo/chart/publish",
            method="POST",
            data={"content": "print('chart')\n"},
        )
        self.assertEqual(
            json.loads(output.getvalue()), {"success": True, "version": "v1"}
        )

    def test_publish_human_output_shows_formal_url_not_version(self):
        args = SimpleNamespace(
            server="http://localhost:8000",
            project="demo",
            name="chart",
            file=None,
            stdin=False,
            json=False,
        )
        output = io.StringIO()

        with (
            patch.object(
                self.tool_cli,
                "_read_publish_content",
                return_value="print('chart')\n",
            ),
            patch.object(
                self.tool_cli,
                "make_request",
                return_value={
                    "success": True,
                    "version": "v1",
                    "url": "/user/tools/demo/chart",
                },
            ),
            redirect_stdout(output),
        ):
            self.tool_cli.cmd_publish(args)

        text = output.getvalue()
        self.assertIn("✓ 发布成功: demo/chart", text)
        self.assertIn("正式地址: http://localhost:8000/user/tools/demo/chart", text)
        self.assertNotIn("version:", text)

    def test_preview_with_project_name_uses_fixed_preview_endpoint(self):
        args = SimpleNamespace(
            server="http://localhost:8000",
            project="demo",
            name="chart",
            file="chart.py",
            stdin=False,
            json=True,
        )
        output = io.StringIO()

        with (
            patch.object(self.tool_cli, "_read_tool_content", return_value="code"),
            patch.object(
                self.tool_cli,
                "make_request",
                return_value={
                    "url": "/client/tool/demo/chart",
                    "preview_url": "/client/tool/demo/chart",
                    "log_url": "/api/tools/preview/log/fixed/demo/chart",
                    "key": "fixed-demo-chart",
                    "message": "预览已更新",
                },
            ) as request_mock,
            redirect_stdout(output),
        ):
            self.tool_cli.cmd_preview(args)

        request_mock.assert_called_once_with(
            "http://localhost:8000/api/tools/preview/demo/chart",
            method="POST",
            data={"content": "code"},
        )
        payload = json.loads(output.getvalue())
        self.assertEqual(
            payload["preview_url"], "http://localhost:8000/client/tool/demo/chart"
        )
        self.assertEqual(
            payload["log_url"],
            "http://localhost:8000/api/tools/preview/log/fixed/demo/chart",
        )

    def test_preview_without_project_name_keeps_temporary_preview_endpoint(self):
        args = SimpleNamespace(
            server="http://localhost:8000",
            project=None,
            name=None,
            file="chart.py",
            stdin=False,
            json=True,
        )

        with (
            patch.object(self.tool_cli, "_read_tool_content", return_value="code"),
            patch.object(
                self.tool_cli,
                "make_request",
                return_value={
                    "url": "/client/tool/token",
                    "key": "token",
                    "message": "上传成功",
                },
            ) as request_mock,
            redirect_stdout(io.StringIO()),
        ):
            self.tool_cli.cmd_preview(args)

        request_mock.assert_called_once_with(
            "http://localhost:8000/api/tools/preview",
            method="POST",
            data={"content": "code"},
        )

    def test_prelog_with_project_name_uses_fixed_log_endpoint(self):
        args = SimpleNamespace(
            server="http://localhost:8000",
            target="demo",
            name="chart",
            lines=20,
            grep=None,
            follow=False,
        )
        output = io.StringIO()

        with (
            patch.object(
                self.tool_cli,
                "make_raw_request",
                return_value=(200, "started\n"),
            ) as request_mock,
            redirect_stdout(output),
        ):
            self.tool_cli.cmd_prelog(args)

        request_mock.assert_called_once_with(
            "http://localhost:8000/api/tools/preview/log/fixed/demo/chart?lines=20"
        )
        self.assertIn("预览日志: demo/chart", output.getvalue())

    def test_status_uses_project_name_state_endpoint(self):
        args = SimpleNamespace(
            server="http://localhost:8000",
            project="demo",
            name="chart",
            json=True,
        )
        output = io.StringIO()

        with (
            patch.object(
                self.tool_cli,
                "make_request",
                return_value={
                    "success": True,
                    "tool": {"current_version": "v2"},
                    "state": {"published": True},
                },
            ) as request_mock,
            redirect_stdout(output),
        ):
            self.tool_cli.cmd_status(args)

        request_mock.assert_called_once_with(
            "http://localhost:8000/api/tools/demo/chart/state"
        )
        self.assertEqual(json.loads(output.getvalue())["tool"]["current_version"], "v2")

    def test_variables_lists_keys_without_printing_values(self):
        args = SimpleNamespace(
            server="http://localhost:8000",
            search="接口 地址",
            json=False,
        )
        output = io.StringIO()

        with (
            patch.object(
                self.tool_cli,
                "make_request",
                return_value={
                    "variables": [
                        {
                            "key": "API_BASE",
                            "remark": "接口地址",
                            "value": "secret-value",
                        }
                    ],
                    "total": 1,
                },
            ) as request_mock,
            redirect_stdout(output),
        ):
            self.tool_cli.cmd_variables(args)

        request_mock.assert_called_once_with(
            "http://localhost:8000/api/variables?search=%E6%8E%A5%E5%8F%A3+%E5%9C%B0%E5%9D%80"
        )
        text = output.getvalue()
        self.assertIn("API_BASE", text)
        self.assertIn("接口地址", text)
        self.assertNotIn("secret-value", text)

    def test_variables_parser_is_available(self):
        with (
            patch.object(
                self.tool_cli.sys,
                "argv",
                [
                    "tool-cli.py",
                    "--server",
                    "http://localhost:8000",
                    "variables",
                    "--search",
                    "api",
                ],
            ),
            patch.object(
                self.tool_cli,
                "make_request",
                return_value={"variables": [], "total": 0},
            ) as request_mock,
            redirect_stdout(io.StringIO()),
        ):
            self.tool_cli.main()

        request_mock.assert_called_once_with(
            "http://localhost:8000/api/variables?search=api"
        )


class ToolCliEnvironmentConfigTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool_cli = _load_tool_cli_module()

    def write_config(self, directory: str) -> str:
        path = Path(directory) / "config.toml"
        path.write_text(
            """default_environment = "test"

[environments.test]
url = "https://nicetool.test.example.com/root"
token_env = "NICETOOL_TEST_TOKEN"

[environments.prod]
url = "https://nicetool.example.com/root"
token_env = "NICETOOL_PROD_TOKEN"
production = true
""",
            encoding="utf-8",
        )
        return str(path)

    def test_named_environment_resolves_url_token_and_production(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = self.write_config(directory)
            runtime = self.tool_cli.resolve_runtime(
                explicit_environment="prod",
                explicit_config=config_path,
                environ={"NICETOOL_PROD_TOKEN": "prod-secret"},
            )

        self.assertEqual(runtime["environment"], "prod")
        self.assertEqual(runtime["server"], "https://nicetool.example.com/root")
        self.assertEqual(runtime["token"], "prod-secret")
        self.assertTrue(runtime["production"])

    def test_credentials_file_supplies_environment_token(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = self.write_config(directory)
            credentials_path = Path(directory) / "credentials.env"
            credentials_path.write_text("NICETOOL_TEST_TOKEN=test-secret\n")
            runtime = self.tool_cli.resolve_runtime(
                explicit_config=config_path,
                environ={"NICETOOL_CREDENTIALS": str(credentials_path)},
            )

        self.assertEqual(runtime["token"], "test-secret")

    def test_cli_values_override_environment_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = self.write_config(directory)
            runtime = self.tool_cli.resolve_runtime(
                explicit_environment="prod",
                explicit_config=config_path,
                explicit_server="https://custom.example.com/",
                explicit_token="custom-secret",
                environ={},
            )

        self.assertEqual(runtime["environment"], "custom")
        self.assertEqual(runtime["selected_environment"], "prod")
        self.assertEqual(runtime["server"], "https://custom.example.com")
        self.assertEqual(runtime["token"], "custom-secret")
        self.assertTrue(runtime["production"])

    def test_explicit_server_without_env_bypasses_default_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = self.write_config(directory)
            runtime = self.tool_cli.resolve_runtime(
                explicit_config=config_path,
                explicit_server="https://custom.example.com",
                environ={},
            )

        self.assertEqual(runtime["environment"], "custom")
        self.assertIsNone(runtime["selected_environment"])
        self.assertEqual(runtime["token"], "")
        self.assertFalse(runtime["production"])

    def test_environment_variable_selects_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = self.write_config(directory)
            runtime = self.tool_cli.resolve_runtime(
                explicit_config=config_path,
                environ={
                    "NICETOOL_ENV": "test",
                    "NICETOOL_TEST_TOKEN": "test-secret",
                },
            )

        self.assertEqual(runtime["environment"], "test")
        self.assertEqual(runtime["server"], "https://nicetool.test.example.com/root")

    def test_explicit_missing_config_fails(self):
        with self.assertRaisesRegex(self.tool_cli.ConfigError, "配置文件不存在"):
            self.tool_cli.resolve_runtime(
                explicit_config="/definitely/missing/nicetool.toml",
                environ={},
            )

    def test_missing_named_environment_fails_without_legacy_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = self.write_config(directory)
            with self.assertRaisesRegex(self.tool_cli.ConfigError, "环境不存在"):
                self.tool_cli.resolve_runtime(
                    explicit_environment="staging",
                    explicit_config=config_path,
                    environ={"NICETOOL_URL": "https://wrong.example.com"},
                )

    def test_default_config_path_uses_xdg_config_home(self):
        runtime = self.tool_cli.resolve_runtime(
            environ={"XDG_CONFIG_HOME": "/tmp/custom-config-home"}
        )

        self.assertEqual(
            runtime["config_path"], "/tmp/custom-config-home/nicetool/config.toml"
        )

    def test_nicetool_config_environment_variable_selects_config_file(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = self.write_config(directory)
            runtime = self.tool_cli.resolve_runtime(
                environ={
                    "NICETOOL_CONFIG": config_path,
                    "NICETOOL_TEST_TOKEN": "test-secret",
                }
            )

        self.assertEqual(runtime["environment"], "test")
        self.assertEqual(runtime["server"], "https://nicetool.test.example.com/root")

    def test_production_publish_requires_yes_when_non_interactive(self):
        args = SimpleNamespace(
            server="https://nicetool.example.com",
            environment="prod",
            production=True,
            project="demo",
            name="chart",
            file=None,
            stdin=False,
            json=True,
            yes=False,
        )

        with (
            patch.object(self.tool_cli.sys.stdin, "isatty", return_value=False),
            patch.object(self.tool_cli, "make_request") as request_mock,
            self.assertRaisesRegex(self.tool_cli.ApiError, "--yes"),
        ):
            self.tool_cli.cmd_publish(args)

        request_mock.assert_not_called()

    def test_production_publish_with_yes_uses_selected_server(self):
        args = SimpleNamespace(
            server="https://nicetool.example.com",
            environment="prod",
            production=True,
            project="demo",
            name="chart",
            file=None,
            stdin=False,
            json=True,
            yes=True,
        )
        output = io.StringIO()

        with (
            patch.object(self.tool_cli, "_read_publish_content", return_value="code"),
            patch.object(
                self.tool_cli,
                "make_request",
                return_value={"success": True, "version": "v1"},
            ) as request_mock,
            redirect_stdout(output),
        ):
            self.tool_cli.cmd_publish(args)

        request_mock.assert_called_once_with(
            "https://nicetool.example.com/api/tools/demo/chart/publish",
            method="POST",
            data={"content": "code"},
        )
        self.assertNotIn("prod-secret", output.getvalue())

    def test_create_does_not_require_remote_environment_config(self):
        create_mock = unittest.mock.Mock()
        with (
            patch.object(
                self.tool_cli.sys,
                "argv",
                ["tool-cli.py", "create", "demo", "chart"],
            ),
            patch.object(self.tool_cli, "cmd_create", create_mock),
            patch.dict(
                self.tool_cli.os.environ,
                {"NICETOOL_CONFIG": "/definitely/missing/config.toml"},
                clear=True,
            ),
        ):
            self.tool_cli.main()

        create_mock.assert_called_once()


class ApiFailureStatusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lifecycle = import_module("service.tool_lifecycle_service")
        cls.permission_result = lifecycle.lifecycle_error(
            code="permission_denied",
            message="缺少权限: tool:publish",
            next_action="request_scope",
        )
        cls.tool_api = _load_module_from_path(
            "tool_api_under_test",
            Path(__file__).resolve().parents[1] / "public" / "api" / "tool_api.py",
        )

    def test_v1_lifecycle_permission_denied_maps_to_403(self):
        response = self.tool_api._lifecycle_failure_response(self.permission_result)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(json.loads(response.body)["code"], "permission_denied")


if __name__ == "__main__":
    unittest.main()
