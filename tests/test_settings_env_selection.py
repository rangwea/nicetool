"""环境配置文件选择测试。"""

import unittest

from core.settings import _resolve_env_config


class EnvConfigSelectionTest(unittest.TestCase):
    def test_env_type_selects_environment_file(self) -> None:
        selection = _resolve_env_config(env_file="", env_type="uat")

        self.assertEqual(selection.env_type, "uat")
        self.assertEqual(selection.source, "ENV_TYPE")
        self.assertEqual(selection.env_files, (".env", ".env.uat"))

    def test_env_type_supports_prod(self) -> None:
        selection = _resolve_env_config(env_file="", env_type="prod")

        self.assertEqual(selection.env_type, "prod")
        self.assertEqual(selection.env_files, (".env", ".env.prod"))

    def test_explicit_env_file_has_priority(self) -> None:
        selection = _resolve_env_config(
            env_file="/config/base.env, /secrets/runtime.env",
            env_type="dev",
        )

        self.assertEqual(selection.env_type, "dev")
        self.assertEqual(selection.source, "ENV_FILE")
        self.assertEqual(
            selection.env_files,
            ("/config/base.env", "/secrets/runtime.env"),
        )

    def test_unknown_env_type_fails_fast(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "不支持的 ENV_TYPE"):
            _resolve_env_config(env_file="", env_type="staging")


if __name__ == "__main__":
    unittest.main()
