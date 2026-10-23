import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.auth.actor import (
    ALL_TOOL_SCOPES,
    Actor,
    actor_from_user,
    normalize_scopes,
    require_scope,
    system_actor,
)
from core.auth.dependencies import actor_from_request


class ActorScopeTest(unittest.TestCase):
    def test_admin_user_gets_all_scopes(self):
        user = SimpleNamespace(
            id=7, username="admin", display_name="Admin", role="admin"
        )
        actor = actor_from_user(user)

        self.assertEqual(actor.type, "user")
        self.assertEqual(actor.id, "7")
        self.assertEqual(actor.name, "Admin")
        self.assertTrue(ALL_TOOL_SCOPES.issubset(actor.scopes))

    def test_non_admin_user_gets_read_and_preview_only(self):
        user = SimpleNamespace(id=8, username="dev", display_name="", role="user")
        actor = actor_from_user(user)

        self.assertEqual(actor.scopes, {"tool:read", "tool:preview"})

    def test_token_scopes_are_exact(self):
        user = SimpleNamespace(
            id=9, username="agent", display_name="Agent", role="admin"
        )
        actor = actor_from_user(user, token_scopes={"tool:read", "tool:publish"})

        self.assertEqual(actor.type, "token")
        self.assertEqual(actor.scopes, {"tool:read", "tool:publish"})

    def test_system_actor_has_all_scopes(self):
        actor = system_actor("startup")

        self.assertEqual(actor.type, "system")
        self.assertIn("tool:admin", actor.scopes)

    def test_system_actor_preserves_explicit_empty_scopes(self):
        actor = system_actor("limited", scopes=set())

        self.assertEqual(actor.scopes, set())

    def test_require_scope_raises_permission_error(self):
        actor = Actor(type="token", id="t1", name="token", scopes={"tool:read"})

        with self.assertRaises(PermissionError):
            require_scope(actor, "tool:publish")


class TokenScopeParsingTest(unittest.TestCase):
    def test_normalize_scopes_from_csv(self):
        self.assertEqual(
            normalize_scopes("tool:read, tool:publish,,tool:preview"),
            {"tool:read", "tool:publish", "tool:preview"},
        )


class ActorDependencyTest(unittest.TestCase):
    @patch("core.auth.dependencies.auth_service.is_enabled", return_value=False)
    def test_actor_from_request_uses_system_actor_when_auth_disabled(
        self,
        _is_enabled,
    ):
        request = SimpleNamespace(state=SimpleNamespace())

        actor = actor_from_request(request)

        self.assertEqual(actor.type, "system")
        self.assertEqual(actor.id, "auth-disabled")
        self.assertTrue(ALL_TOOL_SCOPES.issubset(actor.scopes))

    @patch("core.auth.dependencies.auth_service.is_enabled", return_value=True)
    def test_actor_from_request_preserves_token_scopes_when_auth_enabled(
        self,
        _is_enabled,
    ):
        request = SimpleNamespace(
            state=SimpleNamespace(
                user=SimpleNamespace(
                    id=9,
                    username="agent",
                    display_name="Agent",
                    role="admin",
                ),
                auth_token_scopes={"tool:read", "tool:publish"},
            ),
        )

        actor = actor_from_request(request)

        self.assertEqual(actor.type, "token")
        self.assertEqual(actor.id, "9")
        self.assertEqual(actor.name, "Agent")
        self.assertEqual(actor.scopes, {"tool:read", "tool:publish"})


if __name__ == "__main__":
    unittest.main()
