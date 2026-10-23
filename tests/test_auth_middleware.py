"""普通登录入口和 Token 认证回归测试。"""

import json
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from starlette.requests import Request

from core.auth.middleware import AuthMiddleware


def request(path, headers=()):
    return Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "https",
            "server": ("example.com", 443),
            "path": path,
            "query_string": b"tab=mine",
            "headers": list(headers),
        }
    )


class AuthMiddlewareTests(IsolatedAsyncioTestCase):
    def setUp(self):
        self.middleware = AuthMiddleware(app=None)

    async def test_bearer_token_preserves_scopes(self):
        user = SimpleNamespace(id=1)
        req = request("/api/tools", [(b"authorization", b"Bearer cli-token")])
        with patch(
            "core.auth.middleware.auth_service.authenticate_bearer_token_context",
            return_value=(user, ["tools:read"]),
        ) as authenticate:
            self.assertIs(await self.middleware._authenticate(req), user)
        authenticate.assert_called_once_with("cli-token")
        self.assertEqual(req.state.auth_token_scopes, ["tools:read"])

    async def test_cookie_token_authentication(self):
        user = SimpleNamespace(id=1)
        req = request("/user", [(b"cookie", b"session=web-token")])
        with (
            patch("core.auth.middleware.settings.auth_cookie_name", "session"),
            patch(
                "core.auth.middleware.auth_service.authenticate_web_token_context",
                return_value=(user, ["tools:read"]),
            ) as authenticate,
        ):
            self.assertIs(await self.middleware._authenticate(req), user)
        authenticate.assert_called_once_with("web-token")
        self.assertEqual(req.state.auth_token_scopes, ["tools:read"])

    async def test_missing_token_is_unauthenticated(self):
        with patch(
            "core.auth.middleware.auth_service.authenticate_web_token_context",
            return_value=None,
        ):
            self.assertIsNone(await self.middleware._authenticate(request("/user")))

    async def test_page_redirects_to_local_login_with_return_path(self):
        with patch("core.auth.middleware.settings.project_path", "/nicetool"):
            response = self.middleware._unauthorized(request("/nicetool/user"))
        location = urlsplit(response.headers["location"])
        self.assertEqual(location.path, "/nicetool/auth/login")
        self.assertEqual(
            parse_qs(location.query), {"return_to": ["/nicetool/user?tab=mine"]}
        )

    async def test_api_returns_401_without_redirect(self):
        response = self.middleware._unauthorized(request("/api/tools"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.body), {"detail": "需要登录"})
        self.assertNotIn("location", response.headers)
