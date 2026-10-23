"""
枚举管理控制器
支持手动表单、JSON、Java enum 三种方式创建枚举，并管理 key-value-备注
"""

from typing import Any

from nicegui import ui

from core.i18n import html_t, t
from models.enum_definition import EnumDefinitionCreate, EnumDefinitionUpdate
from public.admin.base_controller import BaseController, Menu
from service import enum_parser, enum_service

JAVA_EXAMPLE = """public enum ContentType {
    /**
     * 独立音乐人 垂类
     */
    YIN_YUE_REN(1, "垂类组"),
    /**
     * 内地
     */
    MAINLAND(2, "内地组");
}"""

JSON_EXAMPLE = """[
  {"key": "ACTIVE", "value": "1", "remark": "启用"},
  {"key": "INACTIVE", "value": "0", "remark": "禁用"}
]"""


class EnumManagementController(BaseController):
    """枚举管理"""

    def __init__(self):
        super().__init__()
        self.enums_data: list[dict[str, Any]] = []
        self.search_query = ""

    def menu(self) -> Menu:
        return Menu(icon="list_alt", label="枚举管理", color="primary")

    def render(self):
        self.refresh_data(silent=True)

        with ui.column().classes("w-full gap-3"):
            with ui.row().classes("w-full justify-between items-start gap-3 flex-wrap"):
                with ui.column().classes("gap-0.5"):
                    ui.label(t("枚举管理")).classes(
                        "text-lg font-semibold app-text-primary"
                    )
                    ui.label(t("集中维护业务枚举及其键值映射")).classes(
                        "text-xs text-gray-500"
                    )
                with ui.row().classes("gap-2"):
                    ui.button(t("刷新"), on_click=self.refresh_data).props(
                        "color=grey-7 outline dense"
                    )
                    ui.button(t("新增枚举"), on_click=self.show_create_dialog).props(
                        "color=primary dense"
                    )

            with (
                ui.card().classes("w-full").props("flat"),
                ui.card_section().classes("w-full py-3 px-3 sm:px-4"),
            ):
                ui.input(
                    placeholder=t("搜索名称或描述..."),
                    on_change=self.on_search_change,
                ).props("outlined dense color=primary clearable").classes("w-full")

            with ui.card().classes("w-full").props("flat"):
                self.render_enum_table()

    @ui.refreshable
    def render_enum_table(self):
        filtered = self.get_filtered_enums()

        if not filtered:
            with ui.column().classes("w-full items-center py-10 gap-1.5"):
                ui.icon("list_alt").classes("text-4xl text-gray-300")
                ui.label(t("暂无枚举定义")).classes("text-sm font-medium text-gray-700")
                ui.label(t("点击「新增枚举」开始创建")).classes("text-sm text-gray-400")
            return

        columns = [
            {
                "name": "id",
                "label": "ID",
                "field": "id",
                "align": "center",
                "sortable": True,
            },
            {
                "name": "name",
                "label": t("名称"),
                "field": "name",
                "align": "left",
                "sortable": True,
            },
            {
                "name": "description",
                "label": t("描述"),
                "field": "description",
                "align": "left",
            },
            {
                "name": "values_summary",
                "label": t("枚举值"),
                "field": "values_summary",
                "align": "left",
            },
            {
                "name": "values_count",
                "label": t("数量"),
                "field": "values_count",
                "align": "center",
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
            ui.table(columns=columns, rows=filtered, row_key="id")
            .props("color=primary flat dense separator=horizontal")
            .classes("w-full")
        )

        table.add_slot(
            "body-cell-values_summary",
            """
            <q-td :props="props">
                <span class="text-grey-8 text-caption">{{ props.value }}</span>
            </q-td>
        """,
        )

        table.add_slot(
            "body-cell-actions",
            html_t("""
            <q-td :props="props">
                <div class="q-gutter-xs">
                    <q-btn icon="format_list_bulleted" color="teal" flat round size="sm"
                           @click="$parent.$emit('values', props.row)">
                        <q-tooltip>管理枚举值</q-tooltip>
                    </q-btn>
                    <q-btn icon="edit" color="primary" flat round size="sm"
                           @click="$parent.$emit('edit', props.row)">
                        <q-tooltip>编辑</q-tooltip>
                    </q-btn>
                    <q-btn icon="delete" color="negative" flat round size="sm"
                           @click="$parent.$emit('delete', props.row)">
                        <q-tooltip>删除</q-tooltip>
                    </q-btn>
                </div>
            </q-td>
        """),
        )

        table.on("values", self.show_values_dialog)
        table.on("edit", self.edit_enum)
        table.on("delete", self.delete_enum)

    def _format_row(self, item: dict[str, Any]) -> dict[str, Any]:
        values = item.get("values") or []
        preview_keys = [v.get("key", "") for v in values[:5]]
        summary = ", ".join(preview_keys)
        if len(values) > 5:
            summary += f" … (+{len(values) - 5})"
        row = dict(item)
        row["values_summary"] = summary or "—"
        row["values_count"] = len(values)
        return row

    def get_filtered_enums(self) -> list[dict[str, Any]]:
        filtered = [self._format_row(item) for item in self.enums_data]
        if self.search_query:
            q = self.search_query.lower()
            filtered = [
                row
                for row in filtered
                if q in str(row.get("name", "")).lower()
                or q in str(row.get("description", "")).lower()
            ]
        return filtered

    def refresh_data(self, silent: bool = False):
        try:
            records = enum_service.list_enum_definitions()
            self.enums_data = [r.model_dump() for r in records]
            self.render_enum_table.refresh()
            if not silent:
                ui.notify(t("数据已刷新"), type="positive")
        except Exception as exc:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            self.logger.error(f"刷新枚举数据失败: {exc}")
            ui.notify(t("刷新失败: {arg0}", arg0=exc), type="negative")

    def on_search_change(self, e):
        self.search_query = e.value or ""
        self.render_enum_table.refresh()

    def _render_values_editor(
        self,
        values: list[dict[str, str]],
        table_refresh: ui.refreshable,
    ):
        """可编辑的枚举值列表（就地修改 values 列表）"""

        @ui.refreshable
        def values_table():
            if not values:
                ui.label(t("暂无枚举值，请在下方添加")).classes(
                    "text-grey-6 text-sm py-4"
                )
                return

            cols = [
                {"name": "key", "label": "Key", "field": "key", "align": "left"},
                {"name": "value", "label": "Value", "field": "value", "align": "left"},
                {
                    "name": "remark",
                    "label": t("备注"),
                    "field": "remark",
                    "align": "left",
                },
                {
                    "name": "actions",
                    "label": t("操作"),
                    "field": "actions",
                    "align": "center",
                },
            ]
            rows = [{**v, "index": i} for i, v in enumerate(values)]
            tbl = (
                ui.table(columns=cols, rows=rows, row_key="index")
                .props("flat dense")
                .classes("w-full")
            )
            tbl.add_slot(
                "body-cell-actions",
                """
                <q-td :props="props">
                    <q-btn icon="edit" color="primary" flat round size="sm"
                           @click="$parent.$emit('edit_value', props.row)" />
                    <q-btn icon="delete" color="negative" flat round size="sm"
                           @click="$parent.$emit('delete_value', props.row)" />
                </q-td>
            """,
            )

            def on_edit_value(e):
                row = e.args
                self._show_value_form_dialog(
                    values,
                    row["index"],
                    values_table.refresh,
                    table_refresh,
                )

            def on_delete_value(e):
                idx = e.args["index"]
                if 0 <= idx < len(values):
                    values.pop(idx)
                    values_table.refresh()
                    table_refresh.refresh()

            tbl.on("edit_value", on_edit_value)
            tbl.on("delete_value", on_delete_value)

        values_table()

        with ui.row().classes("w-full gap-2 items-end mt-2"):
            key_input = ui.input("Key").props("outlined dense").classes("flex-1")
            value_input = ui.input("Value").props("outlined dense").classes("flex-1")
            remark_input = ui.input(t("备注")).props("outlined dense").classes("flex-1")

            def add_value():
                key = (key_input.value or "").strip()
                if not key:
                    ui.notify(t("Key 不能为空"), type="warning")
                    return
                if any(v["key"] == key for v in values):
                    ui.notify(t("Key '{arg0}' 已存在", arg0=key), type="warning")
                    return
                values.append(
                    {
                        "key": key,
                        "value": (value_input.value or key).strip(),
                        "remark": (remark_input.value or "").strip(),
                    }
                )
                key_input.value = ""
                value_input.value = ""
                remark_input.value = ""
                values_table.refresh()
                table_refresh.refresh()

            ui.button(t("添加"), icon="add", on_click=add_value).props(
                "color=primary dense"
            )

    def _show_value_form_dialog(
        self,
        values: list[dict[str, str]],
        index: int,
        values_refresh,
        outer_refresh,
    ):
        current = values[index]
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-lg"):
            ui.label(t("编辑枚举值")).classes("text-lg font-semibold mb-4")
            key_input = (
                ui.input("Key", value=current["key"])
                .props("outlined dense")
                .classes("w-full")
            )
            value_input = (
                ui.input("Value", value=current["value"])
                .props("outlined dense")
                .classes("w-full")
            )
            remark_input = (
                ui.input(t("备注"), value=current["remark"])
                .props("outlined dense")
                .classes("w-full")
            )

            def save():
                key = (key_input.value or "").strip()
                if not key:
                    ui.notify(t("Key 不能为空"), type="warning")
                    return
                if any(i != index and v["key"] == key for i, v in enumerate(values)):
                    ui.notify(t("Key '{arg0}' 已存在", arg0=key), type="warning")
                    return
                values[index] = {
                    "key": key,
                    "value": (value_input.value or key).strip(),
                    "remark": (remark_input.value or "").strip(),
                }
                dialog.close()
                values_refresh()
                outer_refresh()

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button(t("取消"), on_click=dialog.close).props("flat")
                ui.button(t("保存"), on_click=save).props("color=primary")
        dialog.open()

    def show_create_dialog(self):
        draft_values: list[dict[str, str]] = []

        with ui.dialog() as dialog, ui.card().classes("w-full max-w-3xl"):
            ui.label(t("新增枚举")).classes("text-lg font-semibold mb-2")
            name_input = (
                ui.input(t("枚举名称"))
                .props("outlined dense required")
                .classes("w-full")
            )
            desc_input = (
                ui.textarea(t("描述")).props("outlined dense").classes("w-full")
            )

            @ui.refreshable
            def preview_label():
                ui.label(t("当前共 {arg0} 个枚举值", arg0=len(draft_values))).classes(
                    "text-sm text-grey-7 mb-2"
                )

            preview_label()

            with ui.tabs().classes("w-full") as tabs:
                manual_tab = ui.tab(t("手动添加"))
                json_tab = ui.tab(t("JSON 解析"))
                java_tab = ui.tab("Java Enum")

            with ui.tab_panels(tabs, value=manual_tab).classes("w-full"):
                with ui.tab_panel(manual_tab):
                    self._render_values_editor(draft_values, preview_label)

                with ui.tab_panel(json_tab):
                    ui.label(t("粘贴 JSON（对象或数组）")).classes(
                        "text-sm text-grey-7"
                    )
                    json_area = (
                        ui.textarea(value=JSON_EXAMPLE)
                        .props("outlined rows=10")
                        .classes("w-full font-mono text-sm")
                    )

                    def apply_json():
                        try:
                            parsed = enum_parser.parse_json_values(
                                json_area.value or ""
                            )
                            draft_values.clear()
                            draft_values.extend(parsed)
                            preview_label.refresh()
                            ui.notify(
                                t("已解析 {arg0} 个枚举值", arg0=len(parsed)),
                                type="positive",
                            )
                        except Exception as exc:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                            ui.notify(str(exc), type="negative")

                    ui.button(t("解析并预览"), icon="code", on_click=apply_json).props(
                        "color=primary outline dense"
                    )

                with ui.tab_panel(java_tab):
                    ui.label(t("粘贴 Java enum 源码")).classes("text-sm text-grey-7")
                    java_area = (
                        ui.textarea(value=JAVA_EXAMPLE)
                        .props("outlined rows=10")
                        .classes("w-full font-mono text-sm")
                    )

                    def apply_java():
                        try:
                            parsed = enum_parser.parse_java_enum(java_area.value or "")
                            draft_values.clear()
                            draft_values.extend(parsed)
                            preview_label.refresh()
                            ui.notify(
                                t("已解析 {arg0} 个枚举值", arg0=len(parsed)),
                                type="positive",
                            )
                        except Exception as exc:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                            ui.notify(str(exc), type="negative")

                    ui.button(
                        t("解析并预览"), icon="coffee", on_click=apply_java
                    ).props("color=primary outline dense")

            def submit():
                name = (name_input.value or "").strip()
                if not name:
                    ui.notify(t("请填写枚举名称"), type="warning")
                    return
                if not draft_values:
                    ui.notify(t("请至少添加一个枚举值"), type="warning")
                    return
                try:
                    enum_service.create_enum_definition(
                        EnumDefinitionCreate(
                            name=name,
                            description=desc_input.value or "",
                            values=list(draft_values),
                        )
                    )
                    ui.notify(t("枚举 '{arg0}' 创建成功", arg0=name), type="positive")
                    dialog.close()
                    self.refresh_data(silent=True)
                except Exception as exc:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                    ui.notify(str(exc), type="negative")

            with ui.row().classes("w-full justify-end gap-2 mt-6"):
                ui.button(t("取消"), on_click=dialog.close).props("flat")
                ui.button(t("创建"), on_click=submit).props("color=primary")

        dialog.open()

    def show_values_dialog(self, e):
        row = e.args
        enum_id = row["id"]
        detail = enum_service.get_enum_definition(enum_id)
        if not detail:
            ui.notify(t("枚举不存在"), type="warning")
            return

        values: list[dict[str, str]] = [dict(v) for v in (detail.values or [])]

        with ui.dialog() as dialog, ui.card().classes("w-full max-w-3xl"):
            ui.label(t("管理枚举值 — {arg0}", arg0=detail.name)).classes(
                "text-lg font-semibold mb-2"
            )

            @ui.refreshable
            def header_info():
                ui.label(t("共 {arg0} 项", arg0=len(values))).classes(
                    "text-sm text-grey-7 mb-2"
                )

            header_info()
            self._render_values_editor(values, header_info)

            def save_values():
                try:
                    enum_service.update_enum_definition(
                        enum_id,
                        EnumDefinitionUpdate(values=list(values)),
                    )
                    ui.notify(t("枚举值已保存"), type="positive")
                    dialog.close()
                    self.refresh_data(silent=True)
                except Exception as exc:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                    ui.notify(str(exc), type="negative")

            with ui.row().classes("w-full justify-end gap-2 mt-6"):
                ui.button(t("取消"), on_click=dialog.close).props("flat")
                ui.button(t("保存"), on_click=save_values).props("color=primary")

        dialog.open()

    def edit_enum(self, e):
        row = e.args
        enum_id = row["id"]
        detail = enum_service.get_enum_definition(enum_id)
        if not detail:
            ui.notify(t("枚举不存在"), type="warning")
            return

        with ui.dialog() as dialog, ui.card().classes("w-full max-w-lg"):
            ui.label(t("编辑枚举")).classes("text-lg font-semibold mb-4")
            name_input = (
                ui.input(t("名称"), value=detail.name)
                .props("outlined dense required")
                .classes("w-full")
            )
            desc_input = (
                ui.textarea(t("描述"), value=detail.description or "")
                .props("outlined dense")
                .classes("w-full")
            )

            def save():
                name = (name_input.value or "").strip()
                if not name:
                    ui.notify(t("名称不能为空"), type="warning")
                    return
                try:
                    result = enum_service.update_enum_definition(
                        enum_id,
                        EnumDefinitionUpdate(
                            name=name,
                            description=desc_input.value or "",
                        ),
                    )
                    if result:
                        ui.notify(t("保存成功"), type="positive")
                        dialog.close()
                        self.refresh_data(silent=True)
                    else:
                        ui.notify(t("枚举不存在"), type="warning")
                except Exception as exc:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                    ui.notify(str(exc), type="negative")

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button(t("取消"), on_click=dialog.close).props("flat")
                ui.button(t("保存"), on_click=save).props("color=primary")

        dialog.open()

    def delete_enum(self, e):
        row = e.args

        with ui.dialog() as dialog, ui.card().classes("w-full max-w-md"):
            ui.label(t("确认删除")).classes("text-lg font-semibold mb-4")
            ui.label(
                t("确定删除枚举「{arg0}」？此操作不可撤销。", arg0=row["name"])
            ).classes("text-grey-7 mb-6")

            def confirm():
                try:
                    if enum_service.delete_enum_definition(row["id"]):
                        ui.notify(t("删除成功"), type="positive")
                        dialog.close()
                        self.refresh_data(silent=True)
                    else:
                        ui.notify(t("枚举不存在"), type="warning")
                except Exception as exc:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                    ui.notify(str(exc), type="negative")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button(t("取消"), on_click=dialog.close).props("flat")
                ui.button(t("删除"), on_click=confirm).props("color=negative")

        dialog.open()


enum_management_controller = EnumManagementController()
