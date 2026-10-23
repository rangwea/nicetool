"""固定预览的权限和兼容性回归测试。"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.auth.middleware import AuthMiddleware
from public.api.tool_api import router


class FixedPreviewPermissionsTest(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        app.add_middleware(AuthMiddleware)
        self.client = TestClient(app)
        self.user = SimpleNamespace(
            id=1,
            username="alice",
            display_name="Alice",
            role="user",
            is_active=True,
            must_change_password=False,
        )

    def upload(self, username="alice", scopes=None, enabled=True, success=True):
        async def authenticate(request):
            if scopes is not None:
                request.state.auth_token_scopes = scopes
            return self.user

        result = {
            "success": success,
            "url": "/client/tool/alice/chart",
            "message": "ok",
            "key": "fixed-alice-chart",
        }
        if not success:
            result.update(status_code=400, code="missing_main", error="缺少 main")
        with (
            patch("core.auth.service.auth_service.is_enabled", return_value=enabled),
            patch.object(AuthMiddleware, "_authenticate", side_effect=authenticate),
            patch(
                "public.api.tool_api.create_fixed_preview", return_value=result
            ) as create,
        ):
            response = self.client.post(
                f"/api/tools/preview/{username}/chart",
                json={"content": "def main(): pass"},
            )
        return response, create

    def test_read_only_token_cannot_write_own_preview(self):
        response, create = self.upload(scopes={"tool:read"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "permission_denied")
        create.assert_not_called()

    def test_user_can_write_own_preview_using_username_not_display_name(self):
        response, create = self.upload()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["key"], "fixed-alice-chart")
        create.assert_called_once_with("alice", "chart", "def main(): pass")

    def test_user_cannot_overwrite_another_users_preview(self):
        response, create = self.upload("bob")
        self.assertEqual(response.status_code, 403)
        create.assert_not_called()

    def test_preview_token_cannot_overwrite_another_users_preview(self):
        response, create = self.upload("bob", scopes={"tool:preview"})
        self.assertEqual(response.status_code, 403)
        create.assert_not_called()

    def test_admin_can_manage_other_users_previews(self):
        self.user.role = "admin"
        response, create = self.upload("bob")
        self.assertEqual(response.status_code, 200)
        create.assert_called_once()

    def test_admin_read_only_token_still_requires_preview_scope(self):
        self.user.role = "admin"
        response, create = self.upload("bob", scopes={"tool:read"})
        self.assertEqual(response.status_code, 403)
        create.assert_not_called()

    def test_auth_disabled_preserves_arbitrary_namespace(self):
        response, create = self.upload("bob", enabled=False)
        self.assertEqual(response.status_code, 200)
        create.assert_called_once()

    def test_invalid_source_keeps_validation_response(self):
        response, _ = self.upload(success=False)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "missing_main")


if __name__ == "__main__":
    unittest.main()
