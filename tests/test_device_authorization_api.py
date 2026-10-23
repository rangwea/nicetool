from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.auth.middleware import AuthMiddleware
from public.api.auth_api import _device_authorization_html, api_router, router
from service.nicetool_environment_service import resolve_external_base_url


class DeviceAuthorizationApiTest(TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(api_router)
        app.include_router(router)
        app.add_middleware(AuthMiddleware)
        self.client = TestClient(app, base_url="http://example.com")

    def test_anonymous_token_polling_uses_api_route(self):
        with (
            patch("core.auth.service.auth_service.is_enabled", return_value=True),
            patch(
                "core.auth.middleware.AuthMiddleware._authenticate", return_value=None
            ) as authenticate,
            patch(
                "public.api.auth_api.auth_service.exchange_device_authorization",
                return_value={"status": "authorization_pending"},
            ),
        ):
            response = self.client.post(
                "/api/auth/device/token", json={"device_code": "a" * 32}
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "authorization_pending")
        authenticate.assert_not_called()

    def test_start_does_not_require_environment_configuration(self):
        with (
            patch("core.auth.service.auth_service.is_enabled", return_value=True),
            patch(
                "service.nicetool_environment_service.build_client_config",
                side_effect=ValueError("未配置启用的 NiceTool 环境"),
            ) as config,
            patch(
                "public.api.auth_api.auth_service.start_device_authorization",
                return_value={"user_code": "12345678", "device_code": "a" * 32},
            ),
        ):
            response = self.client.post(
                "/api/auth/device/start", json={"token_env": "NICETOOL_PROD_TOKEN"}
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_code"], "12345678")
        config.assert_not_called()

    def test_authorization_form_preserves_external_prefix(self):
        from html.parser import HTMLParser
        from urllib.parse import urljoin

        class FormParser(HTMLParser):
            action = None

            def handle_starttag(self, tag, attrs):
                if tag == "form":
                    self.action = dict(attrs)["action"]

        parser = FormParser()
        parser.feed(_device_authorization_html("12345678"))
        for prefix in ("", "/purchaseadmin", "/other/nested"):
            with self.subTest(prefix=prefix):
                self.assertEqual(
                    urljoin(
                        f"https://example.com{prefix}/auth/device/authorize?code=12345678",
                        parser.action,
                    ),
                    f"https://example.com{prefix}/auth/device/authorize",
                )

    def test_fallback_mount_prefix_is_added_once(self):
        for base_url in ("https://example.com/", "https://example.com/purchaseadmin/"):
            self.assertEqual(
                resolve_external_base_url(
                    base_url, "/purchaseadmin", {"environments": {}}
                ),
                "https://example.com/purchaseadmin",
            )

    def test_fallback_without_mount_prefix(self):
        self.assertEqual(
            resolve_external_base_url("https://example.com/", "", {"environments": {}}),
            "https://example.com",
        )
