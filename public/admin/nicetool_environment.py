"""NiceTool 客户端环境管理。"""

from typing import Any

from nicegui import ui

from core.i18n import html_t, t
from core.logger import get_logger
from core.settings import settings
from models.nicetool_environment import (
    NiceToolEnvironmentCreate,
    NiceToolEnvironmentUpdate,
)
from public.admin.base_controller import BaseController, Menu
from service import nicetool_environment_service as environment_service


class NiceToolEnvironmentController(BaseController):
    """维护 ``/api/init.sh`` 下发的环境配置。"""

    def __init__(self) -> None:
        super().__init__()
        self.logger = get_logger(__name__)
        self.rows: list[dict[str, Any]] = []
        self.load_error = ""

    def menu(self) -> Menu:
        return Menu(icon="lan", label="CLI 环境", color="primary")

    def render(self) -> None:
        with ui.column().classes("w-full gap-3"):
            with ui.row().classes("w-full justify-between items-start gap-3 flex-wrap"):
                with ui.column().classes("gap-0.5 min-w-0"):
                    ui.label(t("NiceTool CLI 环境")).classes(
                        "text-lg font-semibold app-text-primary"
                    )
                    ui.label(
                        t("配置测试、正式等服务地址，并生成客户端初始化脚本")
                    ).classes("text-xs text-gray-500")
                with ui.row().classes("gap-2 shrink-0"):
                    ui.button(t("预览 TOML"), on_click=self._show_preview).props(
                        "outline dense color=grey-7"
                    )
                    ui.button(
                        t("复制初始化命令"), on_click=self._copy_init_command
                    ).props("outline dense color=grey-7")
                    ui.button(t("新增环境"), on_click=self._show_form_dialog).props(
                        "dense color=primary"
                    )

            with ui.element("div").classes("w-full bg-gray-50 rounded-lg px-3 py-2"):
                ui.label(
                    t(
                        "只下发 Token 环境变量名，不保存或传输 Token 值；默认环境必须启用。"
                    )
                ).classes("text-xs text-gray-600")

            self._render_table()
        self._refresh(silent=True)

    @ui.refreshable
    def _render_table(self) -> None:
        if self.load_error:
            with ui.column().classes("w-full items-center py-10 gap-1.5"):
                ui.icon("error_outline").classes("text-4xl text-negative")
                ui.label(t("环境加载失败")).classes("text-sm font-medium text-gray-700")
                ui.label(self.load_error).classes("text-xs text-gray-500")
                ui.button(t("重试"), on_click=self._refresh).props(
                    "flat dense color=primary"
                )
            return
        if not self.rows:
            with ui.column().classes("w-full items-center py-10 gap-1.5"):
                ui.icon("lan").classes("text-4xl text-gray-300")
                ui.label(t("暂无 CLI 环境")).classes(
                    "text-sm font-medium text-gray-700"
                )
                ui.label(
                    t("新增并设置一个启用的默认环境后即可使用 /api/init.sh")
                ).classes("text-xs text-gray-500")
            return

        columns = [
            {"name": "name", "label": t("环境"), "field": "name", "sortable": True},
            {"name": "url", "label": t("服务地址"), "field": "url"},
            {"name": "token_env", "label": t("Token 变量"), "field": "token_env"},
            {
                "name": "production_label",
                "label": t("类型"),
                "field": "production_label",
            },
            {"name": "enabled_label", "label": t("状态"), "field": "enabled_label"},
            {
                "name": "sort_order",
                "label": t("排序"),
                "field": "sort_order",
                "align": "right",
            },
            {
                "name": "actions",
                "label": t("操作"),
                "field": "actions",
                "align": "center",
            },
        ]
        display_rows = [
            {
                **row,
                "production_label": t("正式" if row["production"] else "非正式"),
                "enabled_label": t("启用" if row["enabled"] else "停用"),
            }
            for row in self.rows
        ]
        table = (
            ui.table(columns=columns, rows=display_rows, row_key="id")
            .props("flat dense separator=horizontal color=primary")
            .classes("w-full")
        )
        table.add_slot(
            "body-cell-name",
            html_t(
                """<q-td :props="props"><span class="text-weight-medium">{{ props.row.name }}</span><q-badge v-if="props.row.is_default" color="primary" class="q-ml-sm">默认</q-badge></q-td>"""
            ),
        )
        table.add_slot(
            "body-cell-actions",
            html_t(
                """<q-td :props="props"><q-btn icon="edit" color="primary" flat round size="sm" @click="$parent.$emit('edit', props.row)"><q-tooltip>编辑</q-tooltip></q-btn><q-btn icon="delete" color="negative" flat round size="sm" @click="$parent.$emit('delete', props.row)"><q-tooltip>删除</q-tooltip></q-btn></q-td>"""
            ),
        )
        table.on("edit", lambda event: self._show_form_dialog(event.args))
        table.on("delete", lambda event: self._show_delete_dialog(event.args))

    def _refresh(self, silent: bool = False) -> None:
        try:
            self.rows = []
            for record in environment_service.list_environments():
                row = record.model_dump()
                self.rows.append(row)
            self.load_error = ""
            self._render_table.refresh()
            if not silent:
                ui.notify(
                    t("已加载 {arg0} 个环境", arg0=len(self.rows)), type="positive"
                )
        except Exception as exc:
            self.logger.exception("刷新 NiceTool 环境失败")
            self.rows = []
            self.load_error = str(exc)
            self._render_table.refresh()
            if not silent:
                ui.notify(t("刷新失败：{arg0}", arg0=exc), type="negative")

    def _show_form_dialog(self, row: dict[str, Any] | None = None) -> None:
        editing = row is not None
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl p-0 gap-0"):
            with ui.card_section().classes("w-full px-4 py-3 border-b border-gray-100"):
                ui.label(t("编辑 CLI 环境" if editing else "新增 CLI 环境")).classes(
                    "text-base font-semibold text-gray-900"
                )
            with (
                ui.card_section().classes("w-full px-4 py-4"),
                ui.grid().classes("w-full grid-cols-1 sm:grid-cols-2 gap-3"),
            ):
                name = (
                    ui.input(t("环境名称"), value=row.get("name", "") if row else "")
                    .props("outlined dense color=primary")
                    .classes("w-full")
                )
                token_env = (
                    ui.input(
                        t("Token 环境变量"),
                        value=row.get("token_env", "") if row else "",
                    )
                    .props("outlined dense color=primary")
                    .classes("w-full")
                )
                url = (
                    ui.input(
                        t("NiceTool 服务地址"),
                        value=row.get("url", "") if row else "",
                    )
                    .props("outlined dense color=primary")
                    .classes("w-full sm:col-span-2")
                )
                sort_order = (
                    ui.number(
                        t("排序"),
                        value=row.get("sort_order", 0) if row else 0,
                        format="%.0f",
                    )
                    .props("outlined dense color=primary")
                    .classes("w-full")
                )
                with ui.column().classes("gap-1"):
                    production = ui.switch(
                        t("正式环境"), value=bool(row and row.get("production"))
                    )
                    enabled = ui.switch(
                        t("启用"), value=True if not row else bool(row.get("enabled"))
                    )
                    is_default = ui.switch(
                        t("设为默认"), value=bool(row and row.get("is_default"))
                    )
                remark = (
                    ui.textarea(t("备注"), value=row.get("remark", "") if row else "")
                    .props("outlined dense color=primary autogrow")
                    .classes("w-full sm:col-span-2")
                )

            def save() -> None:
                values = {
                    "name": name.value or "",
                    "url": url.value or "",
                    "token_env": token_env.value or "",
                    "production": production.value,
                    "enabled": enabled.value,
                    "is_default": is_default.value,
                    "sort_order": int(sort_order.value or 0),
                    "remark": remark.value or "",
                }
                try:
                    if editing:
                        result = environment_service.update_environment(
                            int(row["id"]), NiceToolEnvironmentUpdate(**values)
                        )
                        if not result:
                            raise ValueError("环境不存在，可能已被删除")
                    else:
                        environment_service.create_environment(
                            NiceToolEnvironmentCreate(**values)
                        )
                except Exception as exc:
                    self.logger.exception("保存 NiceTool 环境失败")
                    ui.notify(t("保存失败：{arg0}", arg0=exc), type="negative")
                    return
                dialog.close()
                ui.notify(t("环境已更新" if editing else "环境已创建"), type="positive")
                self._refresh(silent=True)

            with ui.card_actions().classes(
                "w-full justify-end gap-2 px-4 py-3 border-t border-gray-100"
            ):
                ui.button(t("取消"), on_click=dialog.close).props(
                    "flat dense color=grey-7"
                )
                ui.button(t("保存"), on_click=save).props("dense color=primary")
        dialog.open()

    def _show_delete_dialog(self, row: dict[str, Any]) -> None:
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-md"):
            ui.label(t("删除 CLI 环境")).classes(
                "text-base font-semibold text-gray-900"
            )
            ui.label(
                t(
                    "确认删除环境「{arg0}」？客户端下次初始化将不再包含它。",
                    arg0=row.get("name", ""),
                )
            ).classes("text-sm text-gray-600")

            def confirm() -> None:
                try:
                    if not environment_service.delete_environment(int(row["id"])):
                        raise ValueError("环境不存在，可能已被删除")
                except Exception as exc:
                    self.logger.exception("删除 NiceTool 环境失败")
                    ui.notify(t("删除失败：{arg0}", arg0=exc), type="negative")
                    return
                dialog.close()
                ui.notify(t("环境已删除"), type="positive")
                self._refresh(silent=True)

            with ui.card_actions().classes("w-full justify-end gap-2"):
                ui.button(t("取消"), on_click=dialog.close).props(
                    "flat dense color=grey-7"
                )
                ui.button(t("删除"), on_click=confirm).props("dense color=negative")
        dialog.open()

    def _show_preview(self) -> None:
        try:
            content = environment_service.render_config_toml()
        except ValueError as exc:
            ui.notify(t("无法生成配置：{arg0}", arg0=exc), type="warning")
            return
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl"):
            ui.label(t("客户端 TOML 预览")).classes(
                "text-base font-semibold text-gray-900"
            )
            ui.code(content, language="toml").classes("w-full")
            with ui.card_actions().classes("w-full justify-end"):
                ui.button(t("关闭"), on_click=dialog.close).props(
                    "flat dense color=grey-7"
                )
        dialog.open()

    async def _copy_init_command(self) -> None:
        try:
            environment_service.build_client_config()
        except ValueError as exc:
            ui.notify(t("无法生成命令：{arg0}", arg0=exc), type="warning")
            return
        path = settings.path_for("/api/init.sh")
        await ui.run_javascript(
            f"navigator.clipboard.writeText('curl -fsSL ' + window.location.origin + {path!r} + ' | sh')"
        )
        ui.notify(t("初始化命令已复制"), type="positive")


nicetool_environment_controller = NiceToolEnvironmentController()
