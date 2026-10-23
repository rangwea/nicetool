"""认证用户显示组件。"""

import json

from nicegui import ui

from core.auth.service import auth_service
from core.i18n import option_labels, t
from core.settings import settings


def _format_datetime(value: str | None) -> str:
    if not value:
        return "-"
    return value.replace("T", " ")[:16]


async def _copy_text(value: str, message: str = "已复制") -> None:
    if not value:
        ui.notify(t("没有可复制的内容"), type="warning")
        return
    try:
        await ui.run_javascript(
            f"await navigator.clipboard.writeText({json.dumps(value)})"
        )
        ui.notify(t(message), type="positive")
    except Exception:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        ui.notify(t("复制失败，请手动复制"), type="negative")


def get_current_auth_user():
    """从当前 NiceGUI 请求中的 JWT 或中间件状态读取用户。"""
    try:
        request = ui.context.client.request
        state_user = getattr(request.state, "user", None)
        if state_user:
            return state_user
        token = request.cookies.get(settings.auth_cookie_name, "")
    except Exception:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        return None
    context = auth_service.authenticate_web_token_context(token)
    return context[0] if context else None


def show_token_manager_dialog(user) -> None:
    """展示个人访问令牌管理弹窗。"""
    generated_token: dict | None = None

    def render_token_row(token: dict, on_revoke) -> None:
        status = "有效" if token.get("is_active") else "已停用"
        status_classes = (
            "text-xs font-medium px-2 py-1 rounded bg-emerald-50 text-emerald-700"
            if token.get("is_active")
            else "text-xs font-medium px-2 py-1 rounded bg-gray-100 text-gray-500"
        )
        token_prefix = token.get("token_prefix") or ""

        async def copy_prefix() -> None:
            await _copy_text(token_prefix, "Token 前缀已复制")

        with (
            ui.element("div").classes(
                "w-full border border-gray-200 rounded-lg px-3 py-3 bg-white"
            ),
            ui.row().classes("w-full items-start justify-between gap-3"),
        ):
            with ui.column().classes("gap-1 min-w-0 flex-1"):
                with ui.row().classes("items-center gap-2 min-w-0"):
                    ui.label(token.get("name") or "default").classes(
                        "text-sm font-medium text-gray-900 truncate"
                    )
                    ui.label(t(status)).classes(status_classes)
                ui.label(f"{token_prefix}...").classes(
                    "text-xs font-mono text-gray-600"
                )
                ui.label(
                    t(
                        "创建 {arg0} · 最后使用 {arg1}",
                        arg0=_format_datetime(token.get("created_at")),
                        arg1=_format_datetime(token.get("last_used_at")),
                    )
                ).classes("text-xs text-gray-500")
                ui.label(t("CLI 全部权限")).classes("text-xs text-gray-400")

            with ui.row().classes("items-center gap-1"):
                copy_button = ui.button(
                    icon="content_copy", on_click=copy_prefix
                ).props("flat round dense color=primary")
                with copy_button:
                    ui.tooltip(t("复制 Token 前缀"))
                if token.get("is_active"):
                    revoke_button = ui.button(
                        icon="block",
                        on_click=lambda _, token_id=token["id"]: on_revoke(token_id),
                    ).props("flat round dense color=negative")
                    with revoke_button:
                        ui.tooltip(t("吊销 Token"))

    with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl p-0 gap-0"):
        with ui.row().classes(
            "w-full items-center justify-between px-5 py-4 border-b border-gray-100"
        ):
            with ui.column().classes("gap-0"):
                ui.label(t("Token 管理")).classes("text-lg font-semibold text-gray-900")
                ui.label(t("个人访问令牌用于 CLI 或 AI agent 调用 API")).classes(
                    "text-xs text-gray-500"
                )
            close_button = ui.button(icon="close", on_click=dialog.close).props(
                "flat round dense"
            )
            with close_button:
                ui.tooltip(t("关闭"))

        if not settings.auth_enable_personal_tokens:
            with ui.column().classes("w-full gap-3 px-5 py-5"):
                ui.label(t("个人访问令牌未启用")).classes(
                    "text-sm font-medium text-gray-800"
                )
                ui.label(t("请先在配置中开启 AUTH_ENABLE_PERSONAL_TOKENS。")).classes(
                    "text-sm text-gray-500"
                )
            dialog.open()
            return

        with ui.tabs().classes("w-full px-5 pt-2") as tabs:
            view_tab = ui.tab(t("查看"))
            create_tab = ui.tab(t("生成"))

        with ui.tab_panels(tabs, value=view_tab).classes("w-full"):
            with ui.tab_panel(view_tab).classes("px-5 py-4"):

                @ui.refreshable
                def token_list() -> None:
                    try:
                        tokens = auth_service.list_personal_tokens(user.id)
                    except Exception as exc:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                        ui.label(t("Token 列表加载失败: {arg0}", arg0=exc)).classes(
                            "text-sm text-red-600"
                        )
                        return

                    if not tokens:
                        with ui.element("div").classes(
                            "w-full border border-dashed border-gray-300 rounded-lg "
                            "px-4 py-8 text-center"
                        ):
                            ui.label(t("还没有生成 Token")).classes(
                                "text-sm font-medium text-gray-800"
                            )
                            ui.label(t("切换到“生成”创建一个新的访问令牌。")).classes(
                                "text-xs text-gray-500 mt-1"
                            )
                        return

                    with ui.column().classes("w-full gap-2"):
                        ui.label(
                            t("历史 Token 只保存哈希，完整明文仅在生成时展示一次。")
                        ).classes(
                            "text-xs text-amber-700 bg-amber-50 px-3 py-2 rounded"
                        )

                        def revoke(token_id: int) -> None:
                            if auth_service.revoke_personal_token(user.id, token_id):
                                ui.notify(t("Token 已吊销"), type="positive")
                                token_list.refresh()

                        for token in tokens:
                            render_token_row(token, revoke)

                token_list()

            with ui.tab_panel(create_tab).classes("px-5 py-4"):
                name_input = (
                    ui.input(t("Token 名称"), value="default")
                    .props("outlined dense clearable")
                    .classes("w-full")
                )
                expiry_input = (
                    ui.select(
                        option_labels(
                            {None: "永不过期", 30: "30 天", 90: "90 天", 365: "1 年"}
                        ),
                        value=90,
                        label=t("有效期"),
                    )
                    .props("outlined dense")
                    .classes("w-full")
                )

                @ui.refreshable
                def generated_token_panel() -> None:
                    if not generated_token:
                        ui.label(
                            t("生成后会在这里显示完整 Token，请立即复制保存。")
                        ).classes("text-sm text-gray-500")
                        return

                    token_value = generated_token.get("token", "")

                    async def copy_token() -> None:
                        await _copy_text(token_value, "Token 已复制")

                    with ui.element("div").classes(
                        "w-full border border-emerald-200 rounded-lg px-3 py-3 "
                        "bg-emerald-50"
                    ):
                        ui.label(t("新 Token 已生成")).classes(
                            "text-sm font-medium text-emerald-800"
                        )
                        ui.label(t("完整明文只显示这一次。")).classes(
                            "text-xs text-emerald-700"
                        )
                        with ui.row().classes("w-full items-center gap-2 mt-3"):
                            ui.input(value=token_value).props(
                                "readonly outlined dense"
                            ).classes("flex-1 font-mono")
                            copy_button = ui.button(
                                icon="content_copy",
                                on_click=copy_token,
                            ).props("round dense color=primary")
                            with copy_button:
                                ui.tooltip(t("复制完整 Token"))

                def create_token() -> None:
                    nonlocal generated_token
                    name = (name_input.value or "default").strip() or "default"
                    try:
                        expires_at = None
                        if expiry_input.value:
                            from datetime import datetime, timedelta

                            expires_at = datetime.now() + timedelta(
                                days=int(expiry_input.value)
                            )
                        generated_token = auth_service.create_personal_token(
                            user.id, name, expires_at=expires_at
                        )
                    except Exception as exc:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                        ui.notify(
                            t("生成 Token 失败: {arg0}", arg0=exc), type="negative"
                        )
                        return

                    ui.notify(t("Token 已生成，请立即复制保存"), type="positive")
                    generated_token_panel.refresh()
                    token_list.refresh()

                with ui.row().classes("w-full justify-end gap-2 mb-4"):
                    ui.button(
                        t("生成 Token"),
                        icon="add",
                        on_click=create_token,
                    ).props("color=primary")

                generated_token_panel()

        dialog.open()


def show_change_password_dialog(user) -> None:
    """修改当前本地账号密码。"""
    with ui.dialog() as dialog, ui.card().classes("w-full max-w-md p-5 gap-4"):
        ui.label(t("修改密码")).classes("text-lg font-semibold")
        current = (
            ui.input(t("当前密码"), password=True, password_toggle_button=True)
            .props("outlined dense")
            .classes("w-full")
        )
        new = (
            ui.input(t("新密码"), password=True, password_toggle_button=True)
            .props("outlined dense")
            .classes("w-full")
        )
        confirm = (
            ui.input(t("确认新密码"), password=True, password_toggle_button=True)
            .props("outlined dense")
            .classes("w-full")
        )

        def submit() -> None:
            if new.value != confirm.value:
                ui.notify(t("两次输入的新密码不一致"), type="warning")
                return
            try:
                auth_service.change_password(
                    user.id, current.value or "", new.value or ""
                )
            except ValueError as exc:
                ui.notify(str(exc), type="negative")
                return
            ui.notify(t("密码已修改"), type="positive")
            dialog.close()

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button(t("取消"), on_click=dialog.close).props("flat")
            ui.button(t("确认修改"), on_click=submit).props("color=primary")
    dialog.open()


def render_current_user(*, compact: bool = False) -> None:
    """在页面右上角或侧栏显示当前登录用户。"""
    user = get_current_auth_user()
    if not user:
        return

    display_name = user.display_name or user.username
    subtitle = user.email or user.username
    initials = (user.username or display_name or "?")[:1].upper()

    with (
        ui.button()
        .props("flat no-caps dense")
        .classes("px-2 py-1 rounded-lg text-gray-800 hover:bg-gray-100")
    ):
        with ui.row().classes("items-center gap-2 min-w-0"):
            if user.avatar_url:
                ui.avatar().props(f'size=sm rounded img="{user.avatar_url}"')
            else:
                with ui.avatar(color="").classes("bg-blue-600").props("size=sm"):
                    ui.label(initials).classes("text-white font-semibold text-sm")

            if not compact:
                with ui.column().classes("gap-0 min-w-0 max-w-[12rem] items-start"):
                    ui.label(display_name).classes(
                        "text-sm font-medium text-gray-900 truncate"
                    )
                    ui.label(subtitle).classes("text-xs text-gray-500 truncate")

            ui.icon("expand_more").classes("text-gray-400 text-base")

        with ui.menu().props('anchor="bottom right" self="top right"'):
            with ui.column().classes("px-3 py-2 min-w-[14rem] gap-0"):
                ui.label(display_name).classes("text-sm font-medium text-gray-900")
                ui.label(subtitle).classes("text-xs text-gray-500")
            ui.separator()
            ui.menu_item(
                t("Token 管理"),
                on_click=lambda: show_token_manager_dialog(user),
            ).props("icon=key")
            if getattr(user, "role", None) == "admin":
                ui.menu_item(
                    t("管理后台"),
                    on_click=lambda: ui.navigate.to(settings.path_for("/admin")),
                ).props("icon=admin_panel_settings")
            if user.password_hash:
                ui.menu_item(
                    t("修改密码"),
                    on_click=lambda: show_change_password_dialog(user),
                ).props("icon=password")
            ui.separator()
            ui.menu_item(
                t("退出登录"),
                on_click=lambda: ui.navigate.to(settings.path_for("/auth/logout")),
            ).props("icon=logout")
