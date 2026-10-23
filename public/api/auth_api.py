"""Authentication routes for local login, external login, JWT, and PATs."""

from html import escape
from urllib.parse import quote

from fastapi import APIRouter, Form, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

from core.auth.dependencies import require_user
from core.auth.service import auth_service
from core.i18n import get_locale, t
from core.settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])
api_router = APIRouter(prefix="/api/auth", tags=["auth"])


def _default_return_to() -> str:
    return settings.path_for("/user")


def _safe_return_to(value: str) -> str:
    if not value.startswith("/") or value.startswith("//"):
        return _default_return_to()
    return value


def _set_web_cookie(response: Response, user) -> None:
    response.set_cookie(
        settings.auth_cookie_name,
        auth_service.issue_web_token(user),
        max_age=settings.auth_jwt_expires_minutes * 60,
        httponly=True,
        secure=settings.auth_require_https_cookie,
        samesite="lax",
        path=settings.get_project_path() or "/",
    )


def _login_html(return_to: str, *, error: str = "") -> str:
    setup = not auth_service.has_local_password_users()
    title = t("初始化管理员" if setup else "登录 NiceTool")
    action = settings.path_for("/auth/setup" if setup else "/auth/login")
    external = ""
    if not setup and auth_service.external_login_enabled():
        href = (
            settings.path_for("/auth/oauth/login")
            + f"?return_to={quote(return_to, safe='')}"
        )
        external = (
            f'<div class="divider"><span>{t("或")}</span></div>'
            f'<a class="sso" href="{href}">{escape(t("使用 {provider} 登录", provider=settings.auth_provider_name))}</a>'
        )
    error_html = f'<div class="error">{escape(t(error))}</div>' if error else ""
    email = (
        f'<label>{t("邮箱")}</label><input name="email" type="email" required autocomplete="email">'
        if setup
        else ""
    )
    subtitle = (
        "创建首个账号，该账号将成为系统管理员。"
        if setup
        else "使用本地账号或统一身份认证登录。"
    )
    return f"""<!doctype html><html lang="{get_locale()}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#f5f7fb;font:14px system-ui;color:#172033}}.card{{width:min(420px,calc(100% - 32px));background:white;border:1px solid #e6eaf0;border-radius:18px;padding:32px;box-shadow:0 18px 55px #24324a16}}h1{{font-size:24px;margin:0 0 8px}}p{{color:#667085;margin:0 0 24px}}label{{display:block;font-weight:600;margin:14px 0 7px}}input{{width:100%;border:1px solid #d0d5dd;border-radius:9px;padding:11px 12px;font:inherit}}button,.sso{{display:block;width:100%;margin-top:22px;padding:11px;border:0;border-radius:9px;text-align:center;text-decoration:none;font-weight:600;cursor:pointer}}button{{background:#2563eb;color:white}}.sso{{margin-top:0;background:#eef4ff;color:#1d4ed8}}.divider{{display:flex;align-items:center;gap:12px;color:#98a2b3;margin:20px 0}}.divider:before,.divider:after{{content:'';height:1px;background:#e4e7ec;flex:1}}.error{{background:#fef3f2;color:#b42318;padding:10px;border-radius:8px;margin-bottom:12px}}</style></head><body><main class="card"><h1>{title}</h1><p>{t(subtitle)}</p>{error_html}<form method="post" action="{action}"><input type="hidden" name="return_to" value="{escape(return_to, quote=True)}"><label>{t("用户名或邮箱")}</label><input name="login" required autocomplete="username">{email}<label>{t("密码")}</label><input name="password" type="password" minlength="10" required autocomplete="current-password"><button type="submit">{title}</button></form>{external}</main></body></html>"""


def _password_html(return_to: str, *, error: str = "") -> str:
    error_html = f'<div class="error">{escape(t(error))}</div>' if error else ""
    action = settings.path_for("/auth/password/change")
    return f"""<!doctype html><html lang="{get_locale()}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{t("修改临时密码")}</title><style>*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#f5f7fb;font:14px system-ui;color:#172033}}main{{width:min(420px,calc(100% - 32px));background:#fff;padding:32px;border-radius:18px;box-shadow:0 18px 55px #24324a16}}h1{{margin:0 0 8px}}p{{color:#667085}}label{{display:block;font-weight:600;margin:14px 0 7px}}input{{width:100%;padding:11px;border:1px solid #d0d5dd;border-radius:9px}}button{{width:100%;margin-top:22px;padding:11px;border:0;border-radius:9px;background:#2563eb;color:#fff;font-weight:600}}.error{{background:#fef3f2;color:#b42318;padding:10px;border-radius:8px}}</style></head><body><main><h1>{t("设置新密码")}</h1><p>{t("当前密码是一次性临时密码，请先修改后继续。")}</p>{error_html}<form method="post" action="{action}"><input type="hidden" name="return_to" value="{escape(return_to, quote=True)}"><label>{t("当前密码")}</label><input name="current_password" type="password" required><label>{t("新密码")}</label><input name="new_password" type="password" minlength="10" required><label>{t("确认新密码")}</label><input name="confirm_password" type="password" minlength="10" required><button>{t("保存并继续")}</button></form></main></body></html>"""


class CreateTokenRequest(BaseModel):
    name: str = Field(default="default", max_length=100)
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10)


class DeviceStartRequest(BaseModel):
    token_env: str = Field(pattern=r"^NICETOOL(?:_[A-Z0-9]+)*_TOKEN$")


class DeviceTokenRequest(BaseModel):
    device_code: str = Field(min_length=32, max_length=200)


@router.get("/login", response_class=HTMLResponse)
async def login_page(return_to: str | None = Query(default=None)):
    return _login_html(_safe_return_to(return_to or _default_return_to()))


@router.post("/setup")
async def setup_admin(
    login: str = Form(),
    email: str = Form(),
    password: str = Form(),
    return_to: str = Form(default="/"),
):
    try:
        user = auth_service.create_initial_admin(login, email, password)
    except ValueError as exc:
        return HTMLResponse(
            _login_html(_safe_return_to(return_to), error=str(exc)), status_code=400
        )
    response = RedirectResponse(_safe_return_to(return_to), status_code=303)
    _set_web_cookie(response, user)
    return response


@router.post("/login")
async def local_login(
    request: Request,
    login: str = Form(),
    password: str = Form(),
    return_to: str = Form(default="/"),
):
    rate_key = (
        f"{request.client.host if request.client else 'unknown'}:"
        f"{login.strip().lower()}"
    )
    if auth_service.login_rate_limited(rate_key):
        raise HTTPException(status_code=429, detail="登录尝试过多，请稍后再试")
    user = auth_service.authenticate_local(login, password)
    if not user:
        auth_service.record_login_failure(rate_key)
        return HTMLResponse(
            _login_html(_safe_return_to(return_to), error="用户名或密码错误"),
            status_code=401,
        )
    auth_service.clear_login_failures(rate_key)
    destination = _safe_return_to(return_to)
    if user.must_change_password:
        destination = (
            settings.path_for("/auth/password/change")
            + f"?return_to={quote(destination, safe='')}"
        )
    response = RedirectResponse(destination, status_code=303)
    _set_web_cookie(response, user)
    return response


@router.get("/oauth/login")
async def oauth_login(request: Request, return_to: str | None = Query(default=None)):
    if not auth_service.external_login_enabled():
        raise HTTPException(status_code=404, detail="外部登录未配置")
    return_to = _safe_return_to(return_to or _default_return_to())
    auth_url, state, nonce = await auth_service.build_authorization_url(
        str(request.url_for("oauth_callback")), return_to
    )
    request.session[auth_service.SESSION_STATE] = state
    request.session[auth_service.SESSION_NONCE] = nonce
    request.session[auth_service.SESSION_RETURN_TO] = return_to
    return RedirectResponse(auth_url)


@router.get("/callback", name="oauth_callback")
async def oauth_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    if error or not code:
        raise HTTPException(status_code=400, detail="外部登录失败")
    expected_state = request.session.pop(auth_service.SESSION_STATE, None)
    if not expected_state or not secrets_compare(state, expected_state):
        raise HTTPException(status_code=400, detail="OAuth state 校验失败")
    token_data = await auth_service.exchange_code(code, str(request.url))
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="未获取到 access_token")
    id_claims = await auth_service.validate_id_token(
        token_data.get("id_token"),
        request.session.pop(auth_service.SESSION_NONCE, None),
    )
    userinfo = await auth_service.fetch_userinfo(access_token)
    claims = {**id_claims, **userinfo}
    user_data = auth_service.map_user_claims(claims)
    if not user_data["subject"]:
        raise HTTPException(status_code=400, detail="用户信息缺少唯一标识")
    user = auth_service.upsert_external_user(user_data)
    return_to = _safe_return_to(
        request.session.pop(auth_service.SESSION_RETURN_TO, _default_return_to())
    )
    response = RedirectResponse(return_to)
    _set_web_cookie(response, user)
    return response


def secrets_compare(left: str | None, right: str) -> bool:
    import secrets

    return bool(left) and secrets.compare_digest(left, right)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    response = RedirectResponse(settings.path_for("/auth/login"))
    response.delete_cookie(
        settings.auth_cookie_name, path=settings.get_project_path() or "/"
    )
    return response


@router.get("/me")
async def me(request: Request):
    user = require_user(request)
    return {"auth_enabled": True, "user": auth_service.user_to_dict(user)}


@router.post("/password")
async def change_password(request: Request, body: ChangePasswordRequest):
    user = require_user(request)
    auth_service.change_password(user.id, body.current_password, body.new_password)
    return {"success": True}


@router.get("/password/change", response_class=HTMLResponse)
async def password_change_page(
    request: Request, return_to: str | None = Query(default=None)
):
    require_user(request)
    return _password_html(_safe_return_to(return_to or _default_return_to()))


@router.post("/password/change")
async def password_change_form(
    request: Request,
    current_password: str = Form(),
    new_password: str = Form(),
    confirm_password: str = Form(),
    return_to: str = Form(default="/"),
):
    user = require_user(request)
    destination = _safe_return_to(return_to)
    if new_password != confirm_password:
        return HTMLResponse(
            _password_html(destination, error="两次输入的新密码不一致"), status_code=400
        )
    try:
        auth_service.change_password(user.id, current_password, new_password)
    except ValueError as exc:
        return HTMLResponse(
            _password_html(destination, error=str(exc)), status_code=400
        )
    return RedirectResponse(destination, status_code=303)


@router.get("/tokens")
async def list_tokens(request: Request):
    user = require_user(request)
    return {"tokens": auth_service.list_personal_tokens(user.id)}


@router.post("/tokens")
async def create_token(request: Request, body: CreateTokenRequest):
    user = require_user(request)
    try:
        expires_at = None
        if body.expires_in_days:
            from datetime import datetime, timedelta

            expires_at = datetime.now() + timedelta(days=body.expires_in_days)
        return auth_service.create_personal_token(
            user.id,
            body.name,
            expires_at=expires_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/tokens/{token_id}")
async def revoke_token(token_id: int, request: Request):
    user = require_user(request)
    if not auth_service.revoke_personal_token(user.id, token_id):
        raise HTTPException(status_code=404, detail="Token 不存在")
    return {"success": True}


@api_router.post("/device/start")
async def start_device_authorization(request: Request, body: DeviceStartRequest):
    grant = auth_service.start_device_authorization(body.token_env)
    grant["verification_uri_complete"] = (
        str(request.url_for("device_authorization_page"))
        + "?code="
        + quote(grant["user_code"], safe="")
    )
    return grant


@api_router.post("/device/token")
async def exchange_device_authorization(body: DeviceTokenRequest):
    return auth_service.exchange_device_authorization(body.device_code)


def _device_authorization_html(code: str, *, approved: bool = False) -> str:
    if approved:
        return f"""<!doctype html><html lang="{get_locale()}"><meta charset="utf-8"><title>{t("授权成功")}</title><body style="font:16px system-ui;display:grid;place-items:center;min-height:90vh"><main><h1>{t("授权成功")}</h1><p>{t("可以关闭此页面并返回终端。")}</p></main></body></html>"""
    action = "authorize"  # 相对当前页面提交，保留反向代理的外部路径前缀。
    return f"""<!doctype html><html lang="{get_locale()}"><meta charset="utf-8"><title>{t("授权 NiceTool")}</title><body style="font:16px system-ui;display:grid;place-items:center;min-height:90vh;background:#f5f7fb"><main style="background:white;padding:32px;border-radius:16px;box-shadow:0 12px 40px #0001"><h1>{t("授权 NiceTool CLI")}</h1><p>{t("确认允许安装脚本创建个人访问 Token。")}</p><p>{t("设备码：")}<strong>{escape(code)}</strong></p><form method="post" action="{action}"><input type="hidden" name="code" value="{escape(code, quote=True)}"><button style="padding:10px 20px;background:#2563eb;color:white;border:0;border-radius:8px">{t("确认授权")}</button></form></main></body></html>"""


@router.get("/device/authorize", response_class=HTMLResponse)
async def device_authorization_page(
    request: Request, code: str = Query(min_length=8, max_length=16)
):
    require_user(request)
    return HTMLResponse(_device_authorization_html(code.strip().upper()))


@router.post("/device/authorize", response_class=HTMLResponse)
async def approve_device_authorization(request: Request, code: str = Form()):
    user = require_user(request)
    if not auth_service.approve_device_authorization(code, user.id):
        raise HTTPException(status_code=400, detail="设备码无效或已过期")
    return HTMLResponse(_device_authorization_html(code, approved=True))
