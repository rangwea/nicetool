"""认证依赖函数，可用于 FastAPI 路由和服务层。"""

from fastapi import HTTPException, Request, status

from core.auth.actor import Actor, actor_from_user, system_actor
from core.auth.service import auth_service
from core.settings import settings
from models.auth import AuthUser


def current_user(request: Request) -> AuthUser | None:
    """获取当前登录用户；未启用认证时返回 None。"""
    if not auth_service.is_enabled():
        return None

    state_user = getattr(request.state, "user", None)
    if state_user:
        return state_user

    token = request.cookies.get(settings.auth_cookie_name, "")
    context = auth_service.authenticate_web_token_context(token)
    user = context[0] if context else None
    request.state.user = user
    return user


def require_user(request: Request) -> AuthUser:
    """要求已登录。"""
    user = current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要登录",
        )
    return user


def require_admin(request: Request) -> AuthUser:
    """要求管理员。"""
    user = require_user(request)
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user


def actor_from_request(request: Request) -> Actor:
    """Build lifecycle actor from request session or bearer token context."""
    if not auth_service.is_enabled():
        return system_actor("auth-disabled")

    user = current_user(request)
    token_scopes = getattr(request.state, "auth_token_scopes", None)
    return actor_from_user(user, token_scopes=token_scopes)
