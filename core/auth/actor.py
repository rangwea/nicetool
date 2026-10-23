"""Lifecycle actor and scope helpers."""

from collections.abc import Iterable
from dataclasses import dataclass, field

from models.auth import AuthUser

TOOL_READ = "tool:read"
TOOL_PREVIEW = "tool:preview"
TOOL_PUBLISH = "tool:publish"
TOOL_ROLLBACK = "tool:rollback"
TOOL_DELETE = "tool:delete"
TOOL_ADMIN = "tool:admin"

ALL_TOOL_SCOPES = {
    TOOL_READ,
    TOOL_PREVIEW,
    TOOL_PUBLISH,
    TOOL_ROLLBACK,
    TOOL_DELETE,
    TOOL_ADMIN,
}

USER_DEFAULT_SCOPES = {TOOL_READ, TOOL_PREVIEW}


@dataclass(frozen=True)
class Actor:
    """Caller identity for lifecycle actions."""

    type: str
    id: str
    name: str
    scopes: set[str] = field(default_factory=set)

    def has_scope(self, scope: str) -> bool:
        return TOOL_ADMIN in self.scopes or scope in self.scopes


def normalize_scopes(scopes: str | Iterable[str] | None) -> set[str]:
    if scopes is None:
        return set()
    if isinstance(scopes, str):
        return {item.strip() for item in scopes.split(",") if item.strip()}
    return {str(item).strip() for item in scopes if str(item).strip()}


def actor_from_user(
    user: AuthUser | object | None,
    *,
    token_scopes: set[str] | None = None,
) -> Actor:
    if user is None:
        return system_actor("anonymous-readonly", scopes={TOOL_READ})

    user_id = str(getattr(user, "id", "") or "")
    username = str(getattr(user, "username", "") or "")
    display_name = str(getattr(user, "display_name", "") or "")
    role = str(getattr(user, "role", "user") or "user")
    name = display_name or username or user_id or "unknown"

    if token_scopes is not None:
        return Actor(type="token", id=user_id, name=name, scopes=set(token_scopes))

    scopes = set(ALL_TOOL_SCOPES) if role == "admin" else set(USER_DEFAULT_SCOPES)
    return Actor(type="user", id=user_id, name=name, scopes=scopes)


def system_actor(name: str = "system", scopes: set[str] | None = None) -> Actor:
    actor_scopes = scopes if scopes is not None else set(ALL_TOOL_SCOPES)
    return Actor(
        type="system",
        id=name,
        name=name,
        scopes=actor_scopes,
    )


def require_scope(actor: Actor, scope: str) -> None:
    if not actor.has_scope(scope):
        raise PermissionError(f"缺少权限: {scope}")
