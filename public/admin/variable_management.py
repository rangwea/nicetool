"""全局工具变量管理。"""

from datetime import datetime
from typing import Any

from nicegui import ui

from core.i18n import html_t, t
from core.logger import get_logger
from models.variable import VariableCreate, VariableUpdate
from public.admin.base_controller import BaseController, Menu
from service import variable_service


class VariableManagementController(BaseController):
    """变量列表与 CRUD 控制器。"""

    def __init__(self) -> None:
        super().__init__()
        self.logger = get_logger(__name__)
        self.rows: list[dict[str, Any]] = []
        self.search_query = ""
        self.load_error = ""

    def menu(self) -> Menu:
        return Menu(icon="data_object", label="变量管理", color="primary")

    def render(self) -> None:
        with ui.column().classes("w-full gap-3"):
            with ui.row().classes("w-full justify-between items-start gap-3 flex-wrap"):
                with ui.column().classes("gap-0.5 min-w-0"):
                    ui.label(t("工具变量")).classes(
                        "text-lg font-semibold app-text-primary"
                    )
                    ui.label(t("集中维护工具运行时可读取的全局字符串配置")).classes(
                        "text-xs text-gray-500"
                    )
                ui.button(t("新增变量"), on_click=self._show_create_dialog).props(
                    "dense color=primary"
                )

            with ui.element("div").classes("w-full bg-gray-50 rounded-lg px-3 py-2"):
                ui.label(
                    t(
                        "工具用法：from core.variable_manager import variables；"
                        "value = variables['KEY']"
                    )
                ).classes("text-xs text-gray-600 font-mono break-all")

            with (
                ui.card().classes("w-full").props("flat"),
                ui.card_section().classes("w-full py-3 px-3 sm:px-4"),
                ui.row().classes("w-full gap-2 items-center flex-wrap"),
            ):
                ui.input(
                    placeholder=t("搜索 Key 或备注"),
                    on_change=self._on_search_change,
                ).props("outlined dense clearable color=primary debounce=250").classes(
                    "min-w-[14rem] flex-1"
                )
                ui.button(t("刷新"), on_click=self._refresh).props(
                    "flat dense color=grey-7"
                )

            self._render_table()

        self._refresh(silent=True)

    @ui.refreshable
    def _render_table(self) -> None:
        if self.load_error:
            with ui.column().classes("w-full items-center py-10 gap-1.5"):
                ui.icon("error_outline").classes("text-4xl text-negative")
                ui.label(t("变量加载失败")).classes("text-sm font-medium text-gray-700")
                ui.label(self.load_error).classes("text-xs text-gray-500")
                ui.button(t("重试"), on_click=self._refresh).props(
                    "flat dense color=primary"
                )
            return

        if not self.rows:
            with ui.column().classes("w-full items-center py-10 gap-1.5"):
                ui.icon("data_object").classes("text-4xl text-gray-300")
                ui.label(t("暂无变量")).classes("text-sm font-medium text-gray-700")
                ui.label(t("点击「新增变量」创建工具配置")).classes(
                    "text-xs text-gray-500"
                )
            return

        columns = [
            {"name": "key", "label": "Key", "field": "key", "sortable": True},
            {"name": "value", "label": "Value", "field": "value"},
            {"name": "remark", "label": t("备注"), "field": "remark"},
            {
                "name": "updated_at",
                "label": t("更新时间"),
                "field": "updated_at",
                "sortable": True,
            },
            {
                "name": "actions",
                "label": t("操作"),
                "field": "actions",
                "align": "center",
            },
        ]
        table = (
            ui.table(columns=columns, rows=self.rows, row_key="id")
            .props("flat dense separator=horizontal color=primary")
            .classes("w-full")
        )
        table.add_slot(
            "body-cell-actions",
            html_t("""
            <q-td :props="props">
                <q-btn icon="edit" color="primary" flat round size="sm"
                       @click="$parent.$emit('edit', props.row)">
                    <q-tooltip>编辑</q-tooltip>
                </q-btn>
                <q-btn icon="delete" color="negative" flat round size="sm"
                       @click="$parent.$emit('delete', props.row)">
                    <q-tooltip>删除</q-tooltip>
                </q-btn>
            </q-td>
            """),
        )
        table.on("edit", lambda event: self._show_edit_dialog(event.args))
        table.on("delete", lambda event: self._show_delete_dialog(event.args))

    def _on_search_change(self, event) -> None:
        self.search_query = event.value or ""
        self._refresh(silent=True)

    @staticmethod
    def _format_time(value: datetime | str | None) -> str:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M")
        if value:
            return str(value).replace("T", " ")[:16]
        return "—"

    def _refresh(self, silent: bool = False) -> None:
        try:
            records = variable_service.list_variables(self.search_query)
            self.rows = []
            for record in records:
                row = record.model_dump()
                row["updated_at"] = self._format_time(record.updated_at)
                self.rows.append(row)
            self.load_error = ""
            self._render_table.refresh()
            if not silent:
                ui.notify(
                    t("已加载 {arg0} 个变量", arg0=len(self.rows)), type="positive"
                )
        except Exception as exc:
            self.logger.exception("刷新变量失败")
            self.load_error = str(exc)
            self.rows = []
            self._render_table.refresh()
            if not silent:
                ui.notify(t("刷新失败：{arg0}", arg0=exc), type="negative")

    def _show_create_dialog(self) -> None:
        self._show_form_dialog()

    def _show_edit_dialog(self, row: dict[str, Any]) -> None:
        self._show_form_dialog(row)

    def _show_form_dialog(self, row: dict[str, Any] | None = None) -> None:
        editing = row is not None
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-xl p-0 gap-0"):
            with ui.card_section().classes("w-full px-4 py-3 border-b border-gray-100"):
                ui.label(t("编辑变量" if editing else "新增变量")).classes(
                    "text-base font-semibold text-gray-900"
                )

            with (
                ui.card_section().classes("w-full px-4 py-4"),
                ui.column().classes("w-full gap-3"),
            ):
                key_input = (
                    ui.input(
                        "Key",
                        value=row.get("key", "") if row else "",
                    )
                    .props("outlined dense color=primary")
                    .classes("w-full")
                )
                value_input = (
                    ui.textarea(
                        "Value",
                        value=row.get("value", "") if row else "",
                    )
                    .props("outlined dense color=primary autogrow")
                    .classes("w-full")
                )
                remark_input = (
                    ui.textarea(
                        t("备注"),
                        value=row.get("remark", "") if row else "",
                    )
                    .props("outlined dense color=primary autogrow")
                    .classes("w-full")
                )

            def save() -> None:
                key = (key_input.value or "").strip()
                if not key:
                    ui.notify(t("Key 不能为空"), type="warning")
                    return
                try:
                    if editing:
                        result = variable_service.update_variable(
                            int(row["id"]),
                            VariableUpdate(
                                key=key,
                                value=value_input.value or "",
                                remark=remark_input.value or "",
                            ),
                        )
                        if not result:
                            raise ValueError("变量不存在，可能已被删除")
                    else:
                        variable_service.create_variable(
                            VariableCreate(
                                key=key,
                                value=value_input.value or "",
                                remark=remark_input.value or "",
                            )
                        )
                except Exception as exc:
                    self.logger.exception("保存变量失败")
                    ui.notify(t("保存失败：{arg0}", arg0=exc), type="negative")
                    return

                dialog.close()
                ui.notify(t("变量已更新" if editing else "变量已创建"), type="positive")
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
            ui.label(t("删除变量")).classes("text-base font-semibold text-gray-900")
            ui.label(
                t(
                    "确认删除变量「{arg0}」？引用它的工具将无法继续读取。",
                    arg0=row.get("key", ""),
                )
            ).classes("text-sm text-gray-600")

            def confirm() -> None:
                try:
                    if not variable_service.delete_variable(int(row["id"])):
                        raise ValueError("变量不存在，可能已被删除")
                except Exception as exc:
                    self.logger.exception("删除变量失败")
                    ui.notify(t("删除失败：{arg0}", arg0=exc), type="negative")
                    return
                dialog.close()
                ui.notify(t("变量已删除"), type="positive")
                self._refresh(silent=True)

            with ui.card_actions().classes("w-full justify-end gap-2"):
                ui.button(t("取消"), on_click=dialog.close).props(
                    "flat dense color=grey-7"
                )
                ui.button(t("删除"), on_click=confirm).props("dense color=negative")

        dialog.open()


variable_management_controller = VariableManagementController()
