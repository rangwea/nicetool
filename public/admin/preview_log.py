"""
预览日志控制器
提供预览工具列表查看和终端日志查看功能
"""

import fcntl
import os
import pty
import signal
import struct
import termios

from nicegui import core, ui

from core.i18n import html_t, t
from core.logger import get_logger
from public.admin.base_controller import BaseController, Menu
from service.preview_service import (
    get_preview_log_file,
    list_previews,
    read_preview_code,
)

logger = get_logger(__name__)


def _format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def _get_preview_tools() -> list[dict]:
    """获取所有预览工具信息"""
    tools = []
    for preview in list_previews():
        tools.append(
            {
                "key": preview["key"],
                "token": preview["key"],
                "type": preview["type"],
                "username": preview.get("username") or "-",
                "tool_name": preview.get("tool_name") or "-",
                "title": preview.get("title") or "(未命名)",
                "url": preview["url"],
                "file_size": _format_size(preview["file_size"]),
                "created_at": preview["created_at"],
                "has_log": preview["has_log"],
                "log_size": _format_size(preview["log_size"])
                if preview["has_log"]
                else "-",
            }
        )

    return tools


class PreviewLogController(BaseController):
    """预览日志控制器"""

    def __init__(self):
        super().__init__()
        self._pty_fd = None
        self._child_pid = None
        self.tools_data: list[dict] = []
        self.search_token = ""
        self.search_title = ""

    def menu(self) -> Menu:
        return Menu(icon="terminal", label="预览日志", color="teal")

    def render(self):
        """渲染预览日志页面"""
        # 初始化数据
        self.refresh_data()

        with ui.column().classes("w-full gap-3"):
            # 页面标题和操作按钮
            with ui.row().classes("w-full justify-between items-start gap-3 flex-wrap"):
                with ui.column().classes("gap-0.5"):
                    ui.label(t("预览日志")).classes(
                        "text-lg font-semibold app-text-primary"
                    )
                    ui.label(t("检查临时预览、固定预览及其运行日志")).classes(
                        "text-xs text-gray-500"
                    )
                with ui.row().classes("gap-2"):
                    ui.button(
                        t("刷新数据"),
                        on_click=self.refresh_data,
                    ).props("color=grey-7 outline dense")

            # 搜索和筛选区域
            with (
                ui.card().classes("w-full").props("flat"),
                ui.card_section().classes("w-full py-3 px-3 sm:px-4"),
                ui.row().classes("w-full gap-2 items-center flex-wrap"),
            ):
                ui.input(
                    placeholder=t("搜索 Key / 用户 / Tool..."),
                    on_change=self._on_search_token_change,
                ).props("outlined dense color=primary clearable").classes(
                    "min-w-[14rem] flex-1"
                )
                ui.input(
                    placeholder=t("搜索工具名称..."),
                    on_change=self._on_search_title_change,
                ).props("outlined dense color=primary clearable").classes(
                    "min-w-[12rem] flex-1"
                )
                ui.button(
                    t("重置"),
                    on_click=self._reset_filters,
                ).props("color=grey-7 flat dense size=sm").classes("ml-auto")

            # 表格区域
            with ui.card().classes("w-full").props("flat"):
                self._render_tool_table()

    def refresh_data(self):
        """刷新预览工具数据"""
        self.tools_data = _get_preview_tools()
        self._render_tool_table.refresh()

    def _on_search_token_change(self, e):
        """Token 搜索条件变化"""
        self.search_token = e.value or ""
        self._render_tool_table.refresh()

    def _on_search_title_change(self, e):
        """工具名称搜索条件变化"""
        self.search_title = e.value or ""
        self._render_tool_table.refresh()

    def _reset_filters(self):
        """重置所有筛选条件"""
        self.search_token = ""
        self.search_title = ""
        self._render_tool_table.refresh()
        ui.notify(t("筛选条件已重置"), type="info")

    def _get_filtered_tools(self) -> list[dict]:
        """获取过滤后的工具列表"""
        filtered = self.tools_data.copy()

        if self.search_token:
            keyword = self.search_token.lower()
            filtered = [
                t
                for t in filtered
                if keyword in t.get("token", "").lower()
                or keyword in t.get("username", "").lower()
                or keyword in t.get("tool_name", "").lower()
            ]

        if self.search_title:
            keyword = self.search_title.lower()
            filtered = [t for t in filtered if keyword in t.get("title", "").lower()]

        return filtered

    @ui.refreshable
    def _render_tool_table(self):
        """渲染预览工具表格"""
        filtered_data = self._get_filtered_tools()

        if not filtered_data:
            with ui.column().classes("w-full items-center py-10 gap-1.5"):
                ui.icon("inbox").classes("text-4xl text-gray-300")
                ui.label(t("暂无预览工具")).classes("text-sm font-medium text-gray-700")
                ui.label(t("通过 API 上传代码后，预览工具会显示在这里")).classes(
                    "text-sm text-gray-400"
                )
            return

        # 表格列定义
        columns = [
            {
                "name": "token",
                "label": "Key",
                "field": "token",
                "sortable": True,
                "align": "left",
            },
            {
                "name": "type",
                "label": t("类型"),
                "field": "type",
                "sortable": True,
                "align": "center",
            },
            {
                "name": "owner",
                "label": t("用户 / Tool"),
                "field": "owner",
                "align": "left",
            },
            {
                "name": "title",
                "label": t("工具名称"),
                "field": "title",
                "sortable": True,
                "align": "left",
            },
            {
                "name": "file_size",
                "label": t("代码大小"),
                "field": "file_size",
                "align": "center",
            },
            {
                "name": "log_size",
                "label": t("日志大小"),
                "field": "log_size",
                "align": "center",
            },
            {
                "name": "created_at",
                "label": t("创建时间"),
                "field": "created_at",
                "sortable": True,
                "align": "center",
            },
            {
                "name": "actions",
                "label": t("操作"),
                "field": "actions",
                "align": "center",
            },
        ]

        rows = [
            {
                "token": t["token"],
                "type": t["type"],
                "owner": f"{t['username']} / {t['tool_name']}",
                "title": t["title"],
                "url": t["url"],
                "file_size": t["file_size"],
                "log_size": t["log_size"],
                "has_log": t["has_log"],
                "created_at": t["created_at"],
            }
            for t in filtered_data
        ]

        # 创建表格
        table = (
            ui.table(
                columns=columns,
                rows=rows,
                row_key="token",
                pagination={"rowsPerPage": 15},
            )
            .props("color=primary flat dense separator=horizontal")
            .classes("w-full")
        )

        # 自定义日志大小列 - 有日志显示绿色，无日志显示灰色
        table.add_slot(
            "body-cell-type",
            html_t("""
            <q-td :props="props">
                <q-badge
                    :color="props.value === 'fixed' ? 'primary' : 'grey-6'"
                    :label="props.value === 'fixed' ? '固定' : '临时'"
                />
            </q-td>
            """),
        )

        # 自定义日志大小列 - 有日志显示绿色，无日志显示灰色
        table.add_slot(
            "body-cell-log_size",
            """
            <q-td :props="props">
                <q-badge
                    :color="props.row.has_log ? 'positive' : 'grey-5'"
                    :label="props.value"
                />
            </q-td>
            """,
        )

        # 自定义操作列
        table.add_slot(
            "body-cell-actions",
            html_t("""
            <q-td :props="props">
                <div class="q-gutter-xs">
                    <q-btn
                        icon="article"
                        color="teal"
                        flat
                        round
                        size="sm"
                        @click="$parent.$emit('view_log', props.row)"
                        :disable="!props.row.has_log"
                    >
                        <q-tooltip>查看日志</q-tooltip>
                    </q-btn>
                    <q-btn
                        icon="code"
                        color="primary"
                        flat
                        round
                        size="sm"
                        @click="$parent.$emit('view_code', props.row)"
                    >
                        <q-tooltip>查看代码</q-tooltip>
                    </q-btn>
                    <q-btn
                        icon="open_in_new"
                        color="info"
                        flat
                        round
                        size="sm"
                        @click="$parent.$emit('open_preview', props.row)"
                    >
                        <q-tooltip>打开预览</q-tooltip>
                    </q-btn>
                </div>
            </q-td>
            """),
        )

        # 绑定事件
        table.on("view_log", lambda e: self._open_log_terminal(e.args))
        table.on("view_code", lambda e: self._open_code_dialog(e.args))
        table.on("open_preview", lambda e: self._open_preview(e.args))

    def _open_preview(self, row: dict):
        """打开预览页面"""
        ui.navigate.to(row["url"], new_tab=True)

    def _open_code_dialog(self, row: dict):
        """打开代码查看对话框"""
        token = row["token"]

        try:
            code_content = read_preview_code(token)
        except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            ui.notify(t("读取代码失败: {arg0}", arg0=e), type="negative")
            return

        if code_content is None:
            ui.notify(t("代码文件不存在"), type="negative")
            return

        with (
            ui.dialog().props("maximized") as dialog,
            ui.card().classes("w-full h-full"),
        ):
            with ui.row().classes("w-full items-center justify-between p-4 border-b"):
                ui.label(t("代码: {arg0}", arg0=token)).classes(
                    "text-lg font-semibold text-gray-700"
                )
                ui.button(icon="close", on_click=dialog.close).props(
                    "flat round size=sm"
                )

            with ui.scroll_area().classes("w-full flex-1 p-4"):
                ui.code(code_content, language="python").classes("w-full")

        dialog.open()

    def _open_log_terminal(self, row: dict):
        """打开终端查看日志"""
        token = row["token"]
        log_file = str(get_preview_log_file(token))

        if not os.path.exists(log_file):
            ui.notify(t("日志文件不存在"), type="negative")
            return

        with (
            ui.dialog().props("maximized") as dialog,
            ui.card().classes("w-full h-full flex flex-col"),
        ):
            # 标题栏
            with ui.row().classes(
                "w-full items-center justify-between px-4 py-2 border-b bg-gray-900"
            ):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("terminal").classes("text-green-400")
                    ui.label(t("日志终端: {arg0}", arg0=token)).classes(
                        "text-sm font-mono text-green-400"
                    )

                with ui.row().classes("gap-1"):
                    ui.button(icon="close", on_click=dialog.close).props(
                        "flat round size=sm color=red-4"
                    )

            # 终端区域
            terminal = ui.xterm(
                {
                    "cursorBlink": True,
                    "fontSize": 13,
                    "theme": {"background": "#1a1a2e"},
                }
            ).classes("w-full flex-1")

            # 状态栏
            with ui.row().classes(
                "w-full items-center justify-between px-4 py-1 border-t bg-gray-800"
            ):
                ui.label(t("文件: {arg0}", arg0=log_file)).classes(
                    "text-xs font-mono text-gray-400"
                )
                with ui.row().classes("gap-2"):
                    ui.label(t("实时跟踪日志，关闭弹窗后自动终止")).classes(
                        "text-xs text-gray-500"
                    )

        async def start_pty():
            """启动 PTY 进程连接终端"""
            await ui.context.client.connected()

            # fork pty
            child_pid, fd = pty.fork()
            if child_pid == 0:
                # 子进程：执行 tail -f
                os.environ["TERM"] = "xterm-256color"
                os.environ["COLORTERM"] = "truecolor"
                os.execvp("tail", ["tail", "-f", "-n", "100", log_file])
            else:
                # 父进程：桥接 pty 和 xterm
                self._pty_fd = fd
                self._child_pid = child_pid

                def read_pty():
                    try:
                        data = os.read(fd, 4096)
                        if data:
                            terminal.write(data.decode("utf-8", errors="replace"))
                    except OSError:
                        pass

                core.loop.add_reader(fd, read_pty)

                @terminal.on_resize
                def on_resize(e):
                    try:
                        cols, rows = e.cols, e.rows
                        winsize = struct.pack("HHHH", rows, cols, 0, 0)
                        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
                    except (OSError, Exception):  # noqa: S110, BLE001 — 终端清理和窗口调整尽力执行，保留失败静默行为。 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                        pass

                cleaned = False

                def cleanup():
                    nonlocal cleaned
                    if cleaned:
                        return
                    cleaned = True
                    try:
                        core.loop.remove_reader(fd)
                    except Exception:  # noqa: S110, BLE001 — 终端清理和窗口调整尽力执行，保留失败静默行为。 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                        pass
                    try:
                        os.close(fd)
                    except Exception:  # noqa: S110, BLE001 — 终端清理和窗口调整尽力执行，保留失败静默行为。 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                        pass
                    try:
                        os.kill(child_pid, signal.SIGKILL)
                        os.waitpid(child_pid, os.WNOHANG)
                    except Exception:  # noqa: S110, BLE001 — 终端清理和窗口调整尽力执行，保留失败静默行为。 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                        pass
                    self._pty_fd = None
                    self._child_pid = None

                ui.context.client.on_delete(cleanup)
                dialog.on("hide", cleanup)

        dialog.on("show", start_pty)
        dialog.open()


preview_log_controller = PreviewLogController()
