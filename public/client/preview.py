from component.language import localized_page

"""
工具预览路由

POST /api/tools/preview 会把代码写入 `_TMP_DIR/{token}.py` 并返回
`/{mount_path}/client/tool/{token}` 这个 URL。

POST /api/tools/preview/{username}/{tool_name} 会覆盖同一个固定预览文件，
并返回 `/{mount_path}/client/tool/{username}/{tool_name}`，便于一边编辑
一边刷新同一个预览页面。
"""

import os

from nicegui import ui

from component.tool_shell import render_tool_shell
from core.logger import (
    get_logger,
    get_preview_logger,
    preview_log_context,
    setup_preview_logging,
)
from service.preview_service import (
    fixed_preview_key_from_path,
    get_preview_file,
    validate_preview_key,
)
from service.tool_runtime import load_tool_entrypoint

logger = get_logger(__name__)


def _render_error(title: str, message: str, detail: str | None = None) -> None:
    """渲染统一风格的错误提示页面"""
    with ui.column().classes("items-center justify-center min-h-screen gap-4"):
        ui.icon("error_outline", size="4rem").classes("text-red-500")
        ui.label(title).classes("text-2xl font-bold text-red-600")
        ui.label(message).classes("text-gray-600 text-center max-w-md")
        if detail:
            ui.label(detail).classes("text-xs text-gray-400 mt-2 max-w-md break-all")


@localized_page("/client/tool/{token}")
async def preview_handler(token: str) -> None:
    """临时工具预览页面

    从预览目录加载临时上传的工具代码并执行。
    """
    preview_key = validate_preview_key(token)
    if preview_key is None:
        _render_error("预览地址无效", "预览 key 包含不支持的字符。", f"key: {token}")
        return
    await _render_preview(preview_key=preview_key, subtitle=f"token {token[:16]}...")


@localized_page("/client/tool/{username}/{tool_name}")
async def fixed_preview_handler(username: str, tool_name: str) -> None:
    """固定工具预览页面"""
    preview_key = fixed_preview_key_from_path(username, tool_name)
    await _render_preview(
        preview_key=preview_key,
        subtitle=f"{username}/{tool_name}",
    )


async def _render_preview(preview_key: str, subtitle: str) -> None:
    preview_logger = get_preview_logger(preview_key)
    preview_logger.info(f"开始渲染预览页面: key={preview_key}")

    filepath = get_preview_file(preview_key)

    if not os.path.exists(filepath):
        preview_logger.warning(f"预览文件不存在: {filepath}")
        _render_error(
            "预览已过期",
            "预览链接对应的文件不存在或已被清理，请重新生成预览。",
            f"key: {preview_key}",
        )
        return

    module_name = f"preview_{preview_key.replace('-', '_').replace('.', '_')}"

    # 页面渲染结束后，按钮、表格等事件会在新的异步上下文中执行，无法继承
    # preview_log_context。为用户模块绑定持久日志 handler，并单独记录 NiceGUI
    # 捕获的事件回调异常，确保前端提示的错误也能在预览日志中追踪。
    setup_preview_logging(preview_key, module_name)

    def log_event_exception(exception: Exception) -> None:
        preview_logger.opt(exception=exception).error(
            f"预览事件回调执行失败: {type(exception).__name__}: {exception}"
        )

    ui.on_exception(log_event_exception)

    try:
        with preview_log_context(preview_key):
            main_func, is_async = load_tool_entrypoint(module_name, str(filepath))
            with render_tool_shell(
                title="工具预览",
                subtitle=subtitle,
                mode="preview",
            ):
                if is_async:
                    await main_func()
                else:
                    main_func()
    except Exception as e:
        preview_logger.exception(f"预览工具执行失败: {e}")  # noqa: TRY401 — 保留现有日志消息，堆栈仍由 exception 记录。
        _render_error(
            "工具执行失败",
            "预览代码在运行过程中发生了错误，请查看预览日志获取详情。",
            f"{type(e).__name__}: {e}",
        )
