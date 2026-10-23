from unittest import TestCase
from unittest.mock import Mock, patch

from fastapi import HTTPException

from public.init_script import nicetool_init_script, nicetool_install_script, router


class NiceToolInitScriptTest(TestCase):
    def test_shell_routes_live_only_under_api(self):
        paths = {route.path for route in router.routes}

        self.assertIn("/api/init.sh", paths)
        self.assertIn("/api/install.sh", paths)
        self.assertNotIn("/init.sh", paths)
        self.assertNotIn("/install.sh", paths)

    def test_install_script_uses_current_server_routes(self):
        request = Mock()
        request.base_url = "https://example.com/"
        config = {
            "default_environment": "test",
            "environments": {
                "test": {
                    "url": "https://example.com/base",
                    "token_env": "NICETOOL_TEST_TOKEN",
                    "production": False,
                }
            },
        }
        with (
            patch(
                "public.init_script.nicetool_environment_service.render_install_script",
                return_value="#!/bin/sh\necho install\n",
            ) as render,
            patch(
                "public.init_script.nicetool_environment_service.build_client_config",
                return_value=config,
            ),
            patch("public.init_script.settings.project_path", ""),
        ):
            response = nicetool_install_script(request)

        render.assert_called_once_with(
            download_url="https://example.com/base/api/downloads/nicetool-skill.zip",
            init_url="https://example.com/base/api/init.sh",
            config=config,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_returns_shell_script_without_cache(self):
        with patch(
            "public.init_script.nicetool_environment_service.render_init_script",
            return_value="#!/bin/sh\necho ok\n",
        ):
            response = nicetool_init_script()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertTrue(response.body.startswith(b"#!/bin/sh"))

    def test_invalid_admin_state_returns_service_unavailable(self):
        with (
            patch(
                "public.init_script.nicetool_environment_service.render_init_script",
                side_effect=ValueError("未配置启用的 NiceTool 环境"),
            ),
            self.assertRaises(HTTPException) as caught,
        ):
            nicetool_init_script()

        self.assertEqual(caught.exception.status_code, 503)
