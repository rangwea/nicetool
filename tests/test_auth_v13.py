from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import jwt

from core.auth.actor import ALL_TOOL_SCOPES
from core.auth.service import AuthService


class AuthV13Tests(TestCase):
    def setUp(self):
        self.service = AuthService()

    def test_passwords_use_argon2_and_verify(self):
        encoded = self.service.hash_password("correct-horse-battery")
        self.assertTrue(encoded.startswith("$argon2"))
        self.assertTrue(self.service.verify_password(encoded, "correct-horse-battery"))
        self.assertFalse(self.service.verify_password(encoded, "wrong-password"))

    def test_short_password_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "至少需要 10"):
            self.service.hash_password("short")

    def test_local_login_rate_limit_clears_after_success(self):
        for _ in range(5):
            self.service.record_login_failure("client:alice")
        self.assertTrue(self.service.login_rate_limited("client:alice"))
        self.service.clear_login_failures("client:alice")
        self.assertFalse(self.service.login_rate_limited("client:alice"))

    def test_initial_admin_is_allowed_when_only_external_users_exist(self):
        created = SimpleNamespace(id=10, role="admin")
        with (
            patch.object(self.service, "has_local_password_users", return_value=False),
            patch.object(
                self.service, "create_local_user", return_value=created
            ) as create_user,
        ):
            result = self.service.create_initial_admin(
                "local-admin", "admin@example.com", "correct-horse-battery"
            )

        self.assertIs(result, created)
        create_user.assert_called_once_with(
            "local-admin",
            "admin@example.com",
            "correct-horse-battery",
            role="admin",
            temporary=False,
        )

    def test_initial_admin_is_blocked_after_local_login_exists(self):
        with (
            patch.object(self.service, "has_local_password_users", return_value=True),
            self.assertRaisesRegex(ValueError, "已完成初始化"),
        ):
            self.service.create_initial_admin(
                "second-admin", "second@example.com", "correct-horse-battery"
            )

    def test_oauth_email_is_only_trusted_when_verified_claim_matches(self):
        claims = {
            "sub": "user-7",
            "preferred_username": "Alice",
            "email": " Alice@Example.COM ",
            "email_verified": True,
        }
        with patch("core.auth.service.settings.auth_provider_profile", "oauth2"):
            mapped = self.service.map_user_claims(claims)
        self.assertEqual(mapped["email"], "alice@example.com")
        self.assertTrue(mapped["email_verified"])

        claims["email_verified"] = False
        with patch("core.auth.service.settings.auth_provider_profile", "oauth2"):
            mapped = self.service.map_user_claims(claims)
        self.assertFalse(mapped["email_verified"])

    def test_web_jwt_round_trip_uses_local_active_user(self):
        user = SimpleNamespace(id=9, role="admin")
        with (
            patch(
                "core.auth.service.settings.auth_jwt_secret",
                "test-secret-that-is-definitely-long-enough",
            ),
            patch("core.auth.service.settings.auth_jwt_algorithm", "HS256"),
            patch("core.auth.service.settings.auth_jwt_issuer", "test-issuer"),
            patch("core.auth.service.settings.auth_jwt_audience", "test-web"),
            patch("core.auth.service.settings.auth_jwt_expires_minutes", 5),
            patch.object(self.service, "get_user", return_value=user),
        ):
            token = self.service.issue_web_token(user)
            context = self.service.authenticate_web_token_context(token)

        self.assertIsNotNone(context)
        authenticated, scopes = context
        self.assertEqual(authenticated.id, 9)
        self.assertIn("*", scopes)

    def test_personal_token_always_gets_all_cli_permissions(self):
        record = SimpleNamespace(user_id=9, expires_at=None, last_used_at=None)
        user = SimpleNamespace(id=9, is_active=True)
        session = MagicMock()
        session.exec.return_value.first.return_value = record
        session.get.return_value = user
        database = MagicMock()
        database.session_scope.return_value.__enter__.return_value = session

        with (
            patch("core.auth.service.db_manager", database),
            patch("core.auth.service.settings.auth_enable_personal_tokens", True),
        ):
            context = self.service.authenticate_personal_token_context("nt_test")

        self.assertIsNotNone(context)
        authenticated, scopes = context
        self.assertIs(authenticated, user)
        self.assertEqual(scopes, ALL_TOOL_SCOPES)

    def test_web_jwt_rejects_wrong_audience(self):
        user = SimpleNamespace(id=9, role="user")
        token = jwt.encode(
            {
                "sub": "9",
                "type": "web",
                "iss": "test-issuer",
                "aud": "other",
                "iat": 1_800_000_000,
                "exp": 1_900_000_000,
                "jti": "token-id",
            },
            "test-secret-that-is-definitely-long-enough",
            algorithm="HS256",
        )
        with (
            patch(
                "core.auth.service.settings.auth_jwt_secret",
                "test-secret-that-is-definitely-long-enough",
            ),
            patch("core.auth.service.settings.auth_jwt_algorithm", "HS256"),
            patch("core.auth.service.settings.auth_jwt_issuer", "test-issuer"),
            patch("core.auth.service.settings.auth_jwt_audience", "test-web"),
            patch.object(self.service, "get_user", return_value=user),
        ):
            self.assertIsNone(self.service.authenticate_web_token_context(token))

    def test_generic_oauth_requires_explicit_endpoints(self):
        with (
            patch("core.auth.service.settings.auth_provider_profile", "oauth2"),
            patch("core.auth.service.settings.auth_authorization_endpoint", ""),
            patch("core.auth.service.settings.auth_token_endpoint", ""),
            patch("core.auth.service.settings.auth_userinfo_endpoint", ""),
        ):
            import asyncio

            with self.assertRaisesRegex(ValueError, "必须配置"):
                asyncio.run(self.service.get_provider_metadata())
