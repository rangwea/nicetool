"""通用 OAuth2/OIDC 认证模块。"""

from core.auth.dependencies import current_user, require_admin, require_user
from core.auth.middleware import AuthMiddleware
from core.auth.service import auth_service

__all__ = [
    "AuthMiddleware",
    "auth_service",
    "current_user",
    "require_admin",
    "require_user",
]
