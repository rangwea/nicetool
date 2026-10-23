"""认证保护中间件。"""

from urllib.parse import quote

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from core.auth.service import auth_service
from core.logger import get_logger
from core.settings import settings

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """按路径统一保护页面和 API。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        if not auth_service.is_enabled():
            return await call_next(request)

        path = request.url.path
        auth_endpoint = self._is_authenticated_auth_endpoint(path)
        if self._is_public_path(path) and not auth_endpoint:
            return await call_next(request)

        if not self._is_protected_path(path) and not auth_endpoint:
            return await call_next(request)

        try:
            user = await self._authenticate(request)
        except RuntimeError as exc:
            logger.error(f"认证不可用: path={path}, reason={exc}")
            status_code = 503 if "数据库连接不可用" in str(exc) else 500
            return JSONResponse(status_code=status_code, content={"detail": str(exc)})
        if not user:
            return self._unauthorized(request)

        if not user.is_active:
            return self._forbidden(request, "用户已禁用")

        request.state.user = user
        if user.must_change_password:
            return self._password_change_required(request)
        if self._is_admin_path(path) and user.role != "admin":
            return self._forbidden(request)

        return await call_next(request)

    async def _authenticate(self, request: Request):
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            context = auth_service.authenticate_bearer_token_context(token)
            if context:
                user, scopes = context
                request.state.auth_token_scopes = scopes
                return user
        token = request.cookies.get(settings.auth_cookie_name, "")
        context = auth_service.authenticate_web_token_context(token)
        if context:
            user, scopes = context
            request.state.auth_token_scopes = scopes
            return user
        return None

    def _is_public_path(self, path: str) -> bool:
        return any(
            self._matches(path, prefix)
            for prefix in auth_service.public_path_prefixes()
        )

    def _is_protected_path(self, path: str) -> bool:
        return any(
            self._matches(path, prefix)
            for prefix in auth_service.protected_path_prefixes()
        )

    def _is_admin_path(self, path: str) -> bool:
        return any(
            self._matches(path, prefix) for prefix in auth_service.admin_path_prefixes()
        )

    def _matches(self, path: str, prefix: str) -> bool:
        path = self._strip_mount_path(path)
        if prefix == "/":
            return path == "/"
        return path == prefix or path.startswith(prefix.rstrip("/") + "/")

    def _strip_mount_path(self, path: str) -> str:
        mount_path = settings.get_project_path()
        if mount_path and mount_path != "/" and path.startswith(mount_path + "/"):
            return path[len(mount_path) :]
        if mount_path and path == mount_path:
            return "/"
        return path

    def _is_api_request(self, request: Request) -> bool:
        path = self._strip_mount_path(request.url.path)
        if path.startswith("/api"):
            return True
        accept = request.headers.get("Accept", "")
        return "application/json" in accept

    def _is_authenticated_auth_endpoint(self, path: str) -> bool:
        path = self._strip_mount_path(path)
        return (
            path == "/auth/me"
            or path.startswith(("/auth/password", "/auth/tokens"))
            or path == "/auth/device/authorize"
        )

    def _unauthorized(self, request: Request) -> Response:
        if self._is_api_request(request):
            return JSONResponse(status_code=401, content={"detail": "需要登录"})
        return_to = request.url.path
        if request.url.query:
            return_to += f"?{request.url.query}"
        login_url = (
            f"{settings.path_for('/auth/login')}?return_to={quote(return_to, safe='')}"
        )
        return RedirectResponse(login_url)

    def _forbidden(self, request: Request, detail: str = "需要管理员权限") -> Response:
        if self._is_api_request(request):
            return JSONResponse(status_code=403, content={"detail": detail})
        return Response(
            '<!doctype html><html><head><meta charset="utf-8"><title>需要管理员权限</title></head>'
            '<body style="font-family: system-ui, sans-serif; padding: 32px;">'
            "<h1>需要管理员权限</h1><p>当前账号没有访问管理后台的权限。</p>"
            "</body></html>",
            status_code=403,
            media_type="text/html; charset=utf-8",
        )

    def _password_change_required(self, request: Request) -> Response:
        if self._is_api_request(request):
            return JSONResponse(
                status_code=403, content={"detail": "必须先修改临时密码"}
            )
        return_to = quote(request.url.path, safe="")
        return RedirectResponse(
            f"{settings.path_for('/auth/password/change')}?return_to={return_to}"
        )
