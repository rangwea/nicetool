"""工具页统一外壳：顶栏导航 + 内容区边距（正式路由与预览共用）。"""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Literal

from nicegui import ui

from component.auth_user import render_current_user
from core.i18n import t

TOOL_SHELL_OUTER = "w-full min-h-screen flex flex-col bg-gray-50"
# 顶栏/侧栏：仅浅分割线，不用 shadow（与全站轻量表面一致）
BORDER_SUBTLE = "border-gray-100"
TOOL_SHELL_HEADER_BAR = f"w-full flex-shrink-0 bg-white border-b {BORDER_SUBTLE}"
PLATFORM_SIDEBAR = f"bg-white border-r {BORDER_SUBTLE}"
SURFACE_CARD = f"border {BORDER_SUBTLE} shadow-none"
TOOL_SHELL_HEADER_INNER = "w-full max-w-screen-2xl mx-auto px-4 sm:px-6 py-3 items-center justify-between gap-3"
TOOL_SHELL_BODY_SCROLL = "flex-1 w-full overflow-y-auto"
TOOL_SHELL_CONTENT = "w-full max-w-screen-2xl mx-auto px-4 sm:px-6 py-4"

ToolShellMode = Literal["tool", "preview"]


def _render_tool_header(
    *,
    title: str | None,
    subtitle: str | None,
    mode: ToolShellMode,
    show_back: bool,
    back_url: str,
) -> None:
    with (
        ui.row().classes(TOOL_SHELL_HEADER_BAR),
        ui.row().classes(TOOL_SHELL_HEADER_INNER),
    ):
        with ui.row().classes("items-center gap-2 min-w-0 flex-1"):
            if show_back:
                ui.button(
                    t("返回工具中心"),
                    on_click=lambda: ui.navigate.to(back_url),
                ).props("flat dense color=primary icon=arrow_back")
            with ui.column().classes("min-w-0 gap-0"):
                if title:
                    ui.label(title).classes(
                        "text-lg font-semibold app-text-primary truncate"
                    )
                if subtitle:
                    ui.label(subtitle).classes("text-sm text-gray-500 truncate")
        if mode == "preview":
            ui.label(t("预览")).classes(
                "text-xs font-medium px-2 py-1 rounded "
                "bg-amber-100 text-amber-800 shrink-0"
            )
        else:
            render_current_user()


@contextmanager
def render_tool_shell(
    *,
    title: str | None = None,
    subtitle: str | None = None,
    mode: ToolShellMode = "tool",
    show_back: bool = True,
    back_url: str = "/user",
    show_header: bool = True,
) -> Generator[None]:
    """包裹工具/预览 UI：顶栏 + 可滚动内容区（max-w-screen-2xl + 边距）。"""
    with ui.column().classes(TOOL_SHELL_OUTER):
        if show_header:
            _render_tool_header(
                title=title,
                subtitle=subtitle,
                mode=mode,
                show_back=show_back,
                back_url=back_url,
            )
        with (
            ui.column().classes(TOOL_SHELL_BODY_SCROLL),
            ui.column().classes(TOOL_SHELL_CONTENT),
        ):
            yield
