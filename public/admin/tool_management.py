"""
工具管理控制器
"""

import json
from typing import Any

from nicegui import ui

from core.auth.actor import system_actor
from core.i18n import html_t, t
from public.admin.base_controller import BaseController, Menu
from service import admin_tool_service, tool_lifecycle_service


class ToolManagementController(BaseController):
    """后台工具管理"""

    def __init__(self):
        super().__init__()
        self.tools_data: list[dict[str, Any]] = []
        self.filter_options: dict[str, list[str]] = {"projects": [], "tags": []}
        self.search_query = ""
        self.project_filter = "all"
        self.selected_tags: list[str] = []

    def menu(self) -> Menu:
        return Menu(icon="construction", label="工具管理", color="primary")

    def render(self):
        self.refresh_data(silent=True)

        with ui.column().classes("w-full gap-3"):
            with ui.row().classes("w-full justify-between items-start gap-3 flex-wrap"):
                with ui.column().classes("gap-0.5"):
                    ui.label(t("工具管理")).classes(
                        "text-lg font-semibold app-text-primary"
                    )
                    ui.label(t("查看工具索引、检索筛选、管理历史版本")).classes(
                        "text-sm text-gray-500"
                    )
                ui.button(t("刷新"), on_click=self.refresh_data).props(
                    "color=grey-7 outline dense"
                )

            self.render_summary()
            self.render_filters()

            with ui.card().classes("w-full").props("flat"):
                self.render_tool_table()

    @ui.refreshable
    def render_summary(self):
        projects = {tool.get("project", "") for tool in self.tools_data}
        published = [tool for tool in self.tools_data if tool.get("current_version")]
        summary = [
            ("工具", len(self.tools_data)),
            ("项目", len(projects)),
            ("已发布", len(published)),
        ]
        with ui.element("div").classes(
            "w-full grid grid-cols-3 gap-px bg-gray-200 rounded-lg overflow-hidden"
        ):
            for label, value in summary:
                with ui.column().classes("bg-white px-3 py-2 gap-0"):
                    ui.label(t(label)).classes("text-xs text-gray-500")
                    ui.label(str(value)).classes("text-sm font-semibold text-gray-900")

    @ui.refreshable
    def render_filters(self):
        with (
            ui.card().classes("w-full").props("flat"),
            ui.card_section().classes("w-full py-3 px-3 sm:px-4"),
            ui.row().classes("w-full gap-2 items-end flex-wrap"),
        ):
            ui.input(
                placeholder=t("搜索工具名称、项目或描述..."),
                value=self.search_query,
                on_change=self.on_search_change,
            ).props("outlined dense color=primary clearable").classes(
                "min-w-[16rem] flex-1"
            )

            project_options = {
                "all": t("全部项目"),
                **{
                    project: project
                    for project in self.filter_options.get("projects", [])
                },
            }
            ui.select(
                options=project_options,
                value=self.project_filter,
                label=t("项目"),
                on_change=self.on_project_change,
            ).props("outlined dense color=primary").classes("min-w-[10rem]")

            tag_options = self.filter_options.get("tags", [])
            ui.select(
                options=tag_options,
                value=self.selected_tags,
                label=t("标签"),
                multiple=True,
                on_change=self.on_tags_change,
            ).props("outlined dense color=primary use-chips clearable").classes(
                "min-w-[14rem] flex-1"
            )

            ui.button(t("重置"), on_click=self.reset_filters).props(
                "color=grey-7 flat dense"
            )

    @ui.refreshable
    def render_tool_table(self):
        if not self.tools_data:
            with ui.column().classes("w-full items-center py-10 gap-1.5"):
                ui.icon("construction").classes("text-4xl text-gray-300")
                ui.label(t("暂无工具")).classes("text-sm font-medium text-gray-700")
                ui.label(t("创建或同步工具后会出现在这里")).classes(
                    "text-sm text-gray-400"
                )
            return

        columns = [
            {
                "name": "display_name",
                "label": t("工具"),
                "field": "display_name",
                "align": "left",
                "sortable": True,
            },
            {
                "name": "project",
                "label": t("项目"),
                "field": "project",
                "align": "left",
                "sortable": True,
            },
            {
                "name": "description",
                "label": t("描述"),
                "field": "description",
                "align": "left",
            },
            {"name": "tags", "label": t("标签"), "field": "tags", "align": "left"},
            {
                "name": "current_version",
                "label": t("当前版本"),
                "field": "current_version",
                "align": "center",
            },
            {
                "name": "versions_count",
                "label": t("历史"),
                "field": "versions_count",
                "align": "center",
                "sortable": True,
            },
            {
                "name": "updated_at",
                "label": t("更新时间"),
                "field": "updated_at",
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
            ui.table(
                columns=columns,
                rows=self.tools_data,
                row_key="id",
                pagination={"rowsPerPage": 10},
            )
            .props("color=primary flat dense separator=horizontal")
            .classes("w-full")
        )

        table.add_slot(
            "body-cell-display_name",
            """
            <q-td :props="props">
                <div class="column">
                    <span class="text-weight-medium">{{ props.row.display_name }}</span>
                    <span class="text-caption text-grey-6">{{ props.row.filename }}</span>
                </div>
            </q-td>
        """,
        )
        table.add_slot(
            "body-cell-description",
            html_t("""
            <q-td :props="props">
                <span class="text-grey-8">
                    {{ props.row.description_preview || '暂无描述' }}
                    <q-tooltip v-if="props.row.description">
                        {{ props.row.description }}
                    </q-tooltip>
                </span>
            </q-td>
        """),
        )
        table.add_slot(
            "body-cell-tags",
            html_t("""
            <q-td :props="props">
                <div class="q-gutter-xs">
                    <q-badge
                        v-for="tag in props.row.tags_list"
                        :key="tag"
                        color="blue-grey-1"
                        text-color="blue-grey-8"
                        :label="tag"
                    />
                    <span v-if="!props.row.tags_list.length" class="text-caption text-grey-5">
                        无标签
                    </span>
                </div>
            </q-td>
        """),
        )
        table.add_slot(
            "body-cell-current_version",
            html_t("""
            <q-td :props="props">
                <q-badge
                    :color="props.value ? 'positive' : 'grey-5'"
                    :label="props.value || '未发布'"
                />
            </q-td>
        """),
        )
        table.add_slot(
            "body-cell-updated_at",
            html_t("""
            <q-td :props="props">
                {{ props.value ? new Date(props.value).toLocaleString('zh-CN') : '-' }}
            </q-td>
        """),
        )
        table.add_slot(
            "body-cell-actions",
            html_t("""
            <q-td :props="props">
                <q-btn
                    icon="dashboard"
                    color="primary"
                    flat
                    round
                    size="sm"
                    @click="$parent.$emit('workspace', props.row)"
                >
                    <q-tooltip>工具工作台</q-tooltip>
                </q-btn>
                <q-btn
                    icon="open_in_new"
                    color="teal"
                    flat
                    round
                    size="sm"
                    @click="$parent.$emit('open_tool', props.row)"
                >
                    <q-tooltip>打开用户页面</q-tooltip>
                </q-btn>
                <q-btn
                    icon="content_copy"
                    color="grey-7"
                    flat
                    round
                    size="sm"
                    @click="$parent.$emit('copy_key', props.row)"
                >
                    <q-tooltip>复制项目.工具名</q-tooltip>
                </q-btn>
                <q-btn
                    icon="history"
                    color="primary"
                    flat
                    round
                    size="sm"
                    @click="$parent.$emit('history', props.row)"
                >
                    <q-tooltip>历史版本</q-tooltip>
                </q-btn>
                <q-btn
                    icon="delete"
                    color="negative"
                    flat
                    round
                    size="sm"
                    @click="$parent.$emit('delete_tool', props.row)"
                >
                    <q-tooltip>删除工具</q-tooltip>
                </q-btn>
            </q-td>
        """),
        )

        table.on("workspace", self.show_tool_workspace)
        table.on("open_tool", self.open_tool_page)
        table.on("copy_key", self.copy_tool_key)
        table.on("history", self.show_versions_dialog)
        table.on("delete_tool", self.confirm_delete_tool)

    def refresh_data(self, silent: bool = False):
        try:
            self.filter_options = admin_tool_service.list_filter_options()
            self.tools_data = admin_tool_service.list_tools(
                search=self.search_query,
                project=self.project_filter,
                tags=self.selected_tags,
            )
            self.render_summary.refresh()
            self.render_filters.refresh()
            self.render_tool_table.refresh()
            if not silent:
                ui.notify(t("工具数据已刷新"), type="positive")
        except Exception as exc:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            self.logger.error(f"刷新工具数据失败: {exc}")
            ui.notify(t("刷新失败: {arg0}", arg0=exc), type="negative")

    def on_search_change(self, e):
        self.search_query = e.value or ""
        self.refresh_data(silent=True)

    def on_project_change(self, e):
        self.project_filter = e.value or "all"
        self.refresh_data(silent=True)

    def on_tags_change(self, e):
        self.selected_tags = e.value or []
        self.refresh_data(silent=True)

    def reset_filters(self):
        self.search_query = ""
        self.project_filter = "all"
        self.selected_tags = []
        self.refresh_data(silent=True)
        ui.notify(t("筛选条件已重置"), type="info")

    def open_tool_page(self, e):
        tool = e.args
        ui.navigate.to(f"/user/tools/{tool['project']}/{tool['name']}", new_tab=True)

    def show_tool_workspace(self, e):
        tool = e.args
        try:
            result = admin_tool_service.get_tool_workspace(tool["id"])
        except Exception as exc:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            self.logger.error(f"加载工具工作台失败: {exc}")
            ui.notify(t("加载工具工作台失败: {arg0}", arg0=exc), type="negative")
            return

        if not result.get("success"):
            ui.notify(result.get("error", "加载工具工作台失败"), type="negative")
            return

        data = result
        workspace_tool = data["tool"]
        with (
            ui.dialog().props("maximized") as dialog,
            ui.card().classes("w-full h-full rounded-none"),
        ):
            with ui.row().classes(
                "w-full items-center justify-between gap-3 px-4 py-3 border-b"
            ):
                with ui.column().classes("gap-0 min-w-0"):
                    ui.label(workspace_tool["display_name"]).classes(
                        "text-lg font-semibold app-text-primary"
                    )
                    ui.label(
                        f"{workspace_tool['project']} / {workspace_tool['filename']}"
                    ).classes("text-sm text-gray-500")
                ui.button(icon="close", on_click=dialog.close).props("flat round dense")

            with (
                ui.scroll_area().classes("w-full h-[calc(100vh-72px)]"),
                ui.column().classes("w-full gap-3 p-4"),
            ):
                self._render_workspace_overview(data)
                self._render_workspace_versions(
                    data["tool"],
                    data.get("versions", []),
                )
                self._render_workspace_events(data.get("events", []))

        dialog.open()

    async def copy_tool_key(self, e):
        tool = e.args
        value = f"{tool['project']}.{tool['name']}"
        try:
            await ui.run_javascript(
                f"await navigator.clipboard.writeText({json.dumps(value)})"
            )
            ui.notify(t("已复制 {arg0}", arg0=value), type="positive")
        except Exception:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            ui.notify(t("复制失败，请手动复制"), type="negative")

    def show_versions_dialog(self, e):
        tool = e.args
        try:
            versions = admin_tool_service.list_tool_versions(tool["id"])
        except Exception as exc:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            self.logger.error(f"获取历史版本失败: {exc}")
            ui.notify(t("获取历史版本失败: {arg0}", arg0=exc), type="negative")
            return

        with ui.dialog() as dialog, ui.card().classes("w-full max-w-5xl"):
            with ui.row().classes("w-full justify-between items-start gap-3 mb-2"):
                with ui.column().classes("gap-0"):
                    ui.label(t("历史版本 - {arg0}", arg0=tool["display_name"])).classes(
                        "text-lg font-semibold app-text-primary"
                    )
                    ui.label(f"{tool['project']} / {tool['filename']}").classes(
                        "text-sm text-gray-500"
                    )
                ui.button(icon="close", on_click=dialog.close).props("flat round dense")

            if not versions:
                with ui.column().classes("w-full items-center py-10"):
                    ui.icon("history").classes("text-5xl text-gray-300")
                    ui.label(t("暂无历史版本")).classes("text-gray-500 mt-3")
            else:
                self._render_versions_table(tool, versions, dialog)

        dialog.open()

    def confirm_delete_tool(self, e):
        tool = e.args
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-md"):
            ui.label(t("确认删除工具")).classes("text-lg font-semibold mb-2")
            ui.label(
                t(
                    "将删除 {arg0} ({arg1} / {arg2})。",
                    arg0=tool["display_name"],
                    arg1=tool["project"],
                    arg2=tool["filename"],
                )
            ).classes("text-gray-700")
            ui.label(
                t("会删除运行缓存、正式版本记录和工具索引，此操作不可撤销。")
            ).classes("text-sm text-red-500 mt-1")

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button(t("取消"), on_click=dialog.close).props("flat")
                ui.button(
                    t("确认删除"),
                    icon="delete",
                    on_click=lambda: self.delete_tool(tool, dialog),
                ).props("color=negative")

        dialog.open()

    def delete_tool(self, tool: dict[str, Any], dialog):
        actor = system_actor("admin-manual-delete")
        result = tool_lifecycle_service.delete_tool(
            actor,
            tool["project"],
            tool["name"],
        )
        if not result.success:
            ui.notify(result.message or "删除工具失败", type="negative")
            return

        ui.notify(t("工具 '{arg0}' 已删除", arg0=tool["display_name"]), type="positive")
        dialog.close()
        self.refresh_data(silent=True)

    def _render_workspace_overview(self, data: dict[str, Any]):
        tool = data["tool"]
        state = data.get("state") or {}
        current = bool(state.get("current"))
        published = bool(state.get("published"))
        indexed = bool(state.get("indexed"))

        with ui.column().classes("w-full gap-2 border border-gray-100 rounded p-3"):
            with ui.row().classes("w-full items-center justify-between gap-2"):
                ui.label(t("概览")).classes("text-sm font-semibold app-text-primary")
                ui.button(
                    icon="open_in_new",
                    on_click=lambda: ui.navigate.to(
                        f"/user/tools/{tool['project']}/{tool['name']}",
                        new_tab=True,
                    ),
                ).props("color=primary flat round dense")

            with ui.row().classes("w-full gap-2 items-center flex-wrap"):
                ui.badge(
                    t("版本 {arg0}", arg0=tool.get("current_version") or "未发布")
                ).props("color=primary outline")
                ui.badge(
                    t("{arg0} 个历史版本", arg0=tool.get("versions_count", 0))
                ).props("color=grey-6 outline")
                ui.badge("已索引" if indexed else "未索引").props(
                    f"color={'positive' if indexed else 'warning'} outline"
                )
                ui.badge("有正式内容" if current else "无正式内容").props(
                    f"color={'positive' if current else 'warning'} outline"
                )
                ui.badge("已发布" if published else "未发布").props(
                    f"color={'positive' if published else 'grey-6'} outline"
                )

            with ui.row().classes("w-full gap-x-6 gap-y-1 flex-wrap text-sm"):
                ui.label(t("创建人: {arg0}", arg0=tool.get("creator") or "-")).classes(
                    "text-gray-600"
                )
                ui.label(
                    t("创建时间: {arg0}", arg0=tool.get("created_at") or "-")
                ).classes("text-gray-600")
                ui.label(
                    t("更新时间: {arg0}", arg0=tool.get("updated_at") or "-")
                ).classes("text-gray-600")
                ui.label(
                    t("发布时间: {arg0}", arg0=tool.get("published_at") or "-")
                ).classes("text-gray-600")

    def _render_workspace_versions(
        self,
        tool: dict[str, Any],
        versions: list[dict[str, Any]],
    ):
        with ui.column().classes("w-full gap-2 border border-gray-100 rounded p-3"):
            ui.label(t("版本")).classes("text-sm font-semibold app-text-primary")
            if not versions:
                ui.label(t("暂无历史版本")).classes("text-sm text-gray-500")
                return

            columns = [
                {
                    "name": "version",
                    "label": t("版本"),
                    "field": "version",
                    "align": "left",
                    "headerClasses": "w-28",
                    "classes": "w-28",
                },
                {
                    "name": "status",
                    "label": t("状态"),
                    "field": "status",
                    "align": "center",
                    "headerClasses": "w-24",
                    "classes": "w-24",
                },
                {
                    "name": "created_by",
                    "label": t("创建人"),
                    "field": "created_by",
                    "align": "center",
                    "headerClasses": "w-32",
                    "classes": "w-32",
                },
                {
                    "name": "published_at",
                    "label": t("时间"),
                    "field": "published_at",
                    "align": "center",
                    "headerClasses": "w-44",
                    "classes": "w-44",
                },
                {
                    "name": "content_sha256",
                    "label": "SHA256",
                    "field": "content_sha256",
                    "align": "left",
                },
            ]
            table = (
                ui.table(
                    columns=columns,
                    rows=versions,
                    row_key="id",
                    pagination={"rowsPerPage": 5},
                )
                .props("flat dense color=primary")
                .classes("w-full")
            )
            table.add_slot(
                "body-cell-version",
                html_t("""
                <q-td :props="props">
                    <div class="row items-center q-gutter-xs no-wrap">
                        <q-badge
                            :color="props.row.is_current ? 'positive' : 'primary'"
                            :label="props.value"
                        />
                        <span v-if="props.row.is_current" class="text-caption text-positive">
                            当前
                        </span>
                    </div>
                </q-td>
            """),
            )
            table.add_slot(
                "body-cell-status",
                """
                <q-td :props="props">
                    <q-badge
                        :color="props.value === 'published' ? 'positive' : 'grey-5'"
                        :label="props.value || '-'"
                    />
                </q-td>
            """,
            )
            table.add_slot(
                "body-cell-published_at",
                html_t("""
                <q-td :props="props">
                    {{ props.value ? new Date(props.value).toLocaleString('zh-CN') : '-' }}
                </q-td>
            """),
            )
            table.add_slot(
                "body-cell-content_sha256",
                """
                <q-td :props="props">
                    <span class="text-caption text-grey-7">
                        {{ props.value ? props.value.slice(0, 16) : '-' }}
                    </span>
                    <q-tooltip v-if="props.value">{{ props.value }}</q-tooltip>
                </q-td>
            """,
            )

    def _render_workspace_events(self, events: list[dict[str, Any]]):
        with ui.column().classes("w-full gap-2 border border-gray-100 rounded p-3"):
            with ui.row().classes("w-full items-center justify-between gap-2"):
                ui.label(t("生命周期事件")).classes(
                    "text-sm font-semibold app-text-primary"
                )
                filter_state = {"value": "all"}
                filter_options = {
                    "all": "全部",
                    "publish": "发布",
                    "rollback": "回滚",
                    "failed": "失败",
                    "system": "系统",
                }

                event_filter = ui.toggle(
                    options=filter_options,
                    value=filter_state["value"],
                    on_change=lambda e: self._on_workspace_event_filter(
                        e,
                        filter_state,
                        render_events_table,
                    ),
                ).props("dense unelevated color=grey-3 toggle-color=primary")
                event_filter.classes("text-xs")

            @ui.refreshable
            def render_events_table():
                filtered_events = self._filter_workspace_events(
                    events,
                    filter_state["value"],
                )
                if not filtered_events:
                    ui.label(t("暂无匹配的生命周期事件")).classes(
                        "text-sm text-gray-500"
                    )
                    return

                columns = [
                    {
                        "name": "action_label",
                        "label": t("动作"),
                        "field": "action_label",
                        "align": "left",
                        "headerClasses": "w-36",
                        "classes": "w-36",
                    },
                    {
                        "name": "actor_name",
                        "label": t("操作者"),
                        "field": "actor_name",
                        "align": "center",
                        "headerClasses": "w-32",
                        "classes": "w-32",
                    },
                    {
                        "name": "actor_type_label",
                        "label": t("来源"),
                        "field": "actor_type_label",
                        "align": "center",
                        "headerClasses": "w-24",
                        "classes": "w-24",
                    },
                    {
                        "name": "version",
                        "label": t("版本"),
                        "field": "version",
                        "align": "center",
                        "headerClasses": "w-24",
                        "classes": "w-24",
                    },
                    {
                        "name": "content_sha256_short",
                        "label": t("指纹"),
                        "field": "content_sha256_short",
                        "align": "center",
                        "headerClasses": "w-32",
                        "classes": "w-32",
                    },
                    {
                        "name": "message",
                        "label": t("说明"),
                        "field": "message",
                        "align": "left",
                    },
                    {
                        "name": "created_at",
                        "label": t("时间"),
                        "field": "created_at",
                        "align": "center",
                        "headerClasses": "w-44",
                        "classes": "w-44",
                    },
                    {
                        "name": "details",
                        "label": t("详情"),
                        "field": "details",
                        "align": "center",
                        "headerClasses": "w-20",
                        "classes": "w-20",
                    },
                ]
                table = (
                    ui.table(
                        columns=columns,
                        rows=filtered_events,
                        row_key="id",
                        pagination={"rowsPerPage": 8},
                    )
                    .props("flat dense color=primary")
                    .classes("w-full")
                )
                table.add_slot(
                    "body-cell-action_label",
                    """
                    <q-td :props="props">
                        <q-badge
                            :color="props.row.success_color"
                            outline
                            :label="props.value"
                        />
                    </q-td>
                """,
                )
                table.add_slot(
                    "body-cell-actor_type_label",
                    """
                    <q-td :props="props">
                        <q-badge color="blue-grey-1" text-color="blue-grey-8" :label="props.value || '-'" />
                    </q-td>
                """,
                )
                table.add_slot(
                    "body-cell-version",
                    """
                    <q-td :props="props">
                        <span class="text-caption text-grey-8">{{ props.value || '-' }}</span>
                    </q-td>
                """,
                )
                table.add_slot(
                    "body-cell-content_sha256_short",
                    """
                    <q-td :props="props">
                        <span class="text-caption text-grey-7">
                            {{ props.value || '-' }}
                        </span>
                        <q-tooltip v-if="props.row.content_sha256">
                            {{ props.row.content_sha256 }}
                        </q-tooltip>
                    </q-td>
                """,
                )
                table.add_slot(
                    "body-cell-message",
                    """
                    <q-td :props="props">
                        <span class="block max-w-[28rem] truncate">
                            {{ props.value || '-' }}
                        </span>
                        <q-tooltip v-if="props.value">{{ props.value }}</q-tooltip>
                    </q-td>
                """,
                )
                table.add_slot(
                    "body-cell-created_at",
                    html_t("""
                    <q-td :props="props">
                        {{ props.value ? new Date(props.value).toLocaleString('zh-CN') : '-' }}
                    </q-td>
                """),
                )
                table.add_slot(
                    "body-cell-details",
                    html_t("""
                    <q-td :props="props">
                        <q-btn
                            icon="info"
                            color="primary"
                            flat
                            round
                            size="sm"
                            @click="$parent.$emit('details', props.row)"
                        >
                            <q-tooltip>查看详情</q-tooltip>
                        </q-btn>
                    </q-td>
                """),
                )
                table.on("details", self.show_lifecycle_event_detail)

            render_events_table()

    def _on_workspace_event_filter(self, e, filter_state, render_events_table):
        filter_state["value"] = e.value or "all"
        render_events_table.refresh()

    def _filter_workspace_events(
        self,
        events: list[dict[str, Any]],
        event_filter: str,
    ) -> list[dict[str, Any]]:
        if event_filter == "failed":
            return [event for event in events if not event.get("success")]
        if event_filter == "system":
            return [event for event in events if event.get("actor_type") == "system"]
        if event_filter == "all":
            return events
        return [event for event in events if event.get("action_group") == event_filter]

    def show_lifecycle_event_detail(self, e):
        event = e.args
        details = event.get("details") or {}
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl"):
            with ui.row().classes("w-full items-center justify-between gap-3 mb-2"):
                with ui.column().classes("gap-0"):
                    ui.label(event.get("action_label") or event.get("action")).classes(
                        "text-lg font-semibold app-text-primary"
                    )
                    ui.label(event.get("created_at") or "-").classes(
                        "text-sm text-gray-500"
                    )
                ui.button(icon="close", on_click=dialog.close).props("flat round dense")

            rows = [
                ("动作", details.get("action") or "-"),
                ("操作者", event.get("actor_name") or "-"),
                ("操作者 ID", details.get("actor_id") or "-"),
                (
                    "来源",
                    event.get("actor_type_label") or event.get("actor_type") or "-",
                ),
                ("结果", event.get("success_label") or "-"),
                ("版本", details.get("version") or "-"),
                ("内容指纹", details.get("content_sha256") or "-"),
                ("说明", event.get("message") or "-"),
            ]
            with ui.column().classes("w-full gap-2"):
                for label, value in rows:
                    with ui.row().classes("w-full gap-3 items-start"):
                        ui.label(t(label)).classes("w-24 text-sm text-gray-500")
                        ui.label(str(value)).classes(
                            "flex-1 text-sm app-text-primary break-all"
                        )

        dialog.open()

    def _render_versions_table(self, tool: dict[str, Any], versions, dialog):
        columns = [
            {
                "name": "version",
                "label": t("版本"),
                "field": "version",
                "align": "left",
            },
            {
                "name": "status",
                "label": t("状态"),
                "field": "status",
                "align": "center",
            },
            {
                "name": "content_size",
                "label": t("大小"),
                "field": "content_size",
                "align": "center",
                "sortable": True,
            },
            {
                "name": "created_by",
                "label": t("创建人"),
                "field": "created_by",
                "align": "center",
            },
            {
                "name": "published_at",
                "label": t("发布时间"),
                "field": "published_at",
                "align": "center",
                "sortable": True,
            },
            {
                "name": "content_sha256",
                "label": "SHA256",
                "field": "content_sha256",
                "align": "left",
            },
            {
                "name": "actions",
                "label": t("操作"),
                "field": "actions",
                "align": "center",
            },
        ]

        table = (
            ui.table(
                columns=columns,
                rows=versions,
                row_key="id",
                pagination={"rowsPerPage": 8},
            )
            .props("flat color=primary")
            .classes("w-full")
        )
        table.add_slot(
            "body-cell-version",
            html_t("""
            <q-td :props="props">
                <div class="row items-center q-gutter-xs">
                    <q-badge
                        :color="props.row.is_current ? 'positive' : 'primary'"
                        :label="props.value"
                    />
                    <span v-if="props.row.is_current" class="text-caption text-positive">
                        当前
                    </span>
                </div>
            </q-td>
        """),
        )
        table.add_slot(
            "body-cell-status",
            """
            <q-td :props="props">
                <q-badge
                    :color="props.value === 'published' ? 'positive' : 'grey-5'"
                    :label="props.value"
                />
            </q-td>
        """,
        )
        table.add_slot(
            "body-cell-content_size",
            """
            <q-td :props="props">
                {{ (props.value / 1024).toFixed(1) }} KB
            </q-td>
        """,
        )
        table.add_slot(
            "body-cell-published_at",
            html_t("""
            <q-td :props="props">
                {{ props.value ? new Date(props.value).toLocaleString('zh-CN') : '-' }}
            </q-td>
        """),
        )
        table.add_slot(
            "body-cell-content_sha256",
            """
            <q-td :props="props">
                <span class="text-caption text-grey-7">
                    {{ props.value ? props.value.slice(0, 12) : '-' }}
                </span>
            </q-td>
        """,
        )
        table.add_slot(
            "body-cell-actions",
            html_t("""
            <q-td :props="props">
                <q-btn
                    icon="code"
                    color="info"
                    flat
                    round
                    size="sm"
                    @click="$parent.$emit('code', props.row)"
                >
                    <q-tooltip>查看代码</q-tooltip>
                </q-btn>
                <q-btn
                    icon="compare_arrows"
                    color="secondary"
                    flat
                    round
                    size="sm"
                    :disable="!props.row.has_previous"
                    @click="$parent.$emit('compare', props.row)"
                >
                    <q-tooltip>与上一版本对比</q-tooltip>
                </q-btn>
                <q-btn
                    icon="settings_backup_restore"
                    color="warning"
                    flat
                    round
                    size="sm"
                    :disable="props.row.is_current || props.row.status !== 'published'"
                    @click="$parent.$emit('rollback', props.row)"
                >
                    <q-tooltip>回滚到此版本</q-tooltip>
                </q-btn>
            </q-td>
        """),
        )
        table.on("code", lambda e: self.show_version_code(tool, e.args))
        table.on("compare", lambda e: self.show_version_diff(tool, e.args))
        table.on("rollback", lambda e: self.confirm_rollback(tool, e.args, dialog))

    def show_version_code(self, tool: dict[str, Any], version: dict[str, Any]):
        result = admin_tool_service.get_version_content(tool["id"], version["id"])
        if not result.get("success"):
            ui.notify(result.get("error", "获取代码失败"), type="negative")
            return

        with ui.dialog() as dialog, ui.card().classes("w-full max-w-6xl"):
            with ui.row().classes("w-full justify-between items-center mb-2"):
                with ui.column().classes("gap-0"):
                    ui.label(t("代码详情 - {arg0}", arg0=result["version"])).classes(
                        "text-lg font-semibold app-text-primary"
                    )
                    ui.label(f"{tool['project']} / {tool['name']}").classes(
                        "text-sm text-gray-500"
                    )
                ui.button(icon="close", on_click=dialog.close).props("flat round dense")

            with ui.scroll_area().classes("w-full h-[70vh] border border-gray-100"):
                ui.code(result.get("content", ""), language="python").classes("w-full")

        dialog.open()

    def show_version_diff(self, tool: dict[str, Any], version: dict[str, Any]):
        result = admin_tool_service.diff_with_previous_version(
            tool["id"],
            version["id"],
        )
        if not result.get("success"):
            ui.notify(result.get("error", "版本对比失败"), type="negative")
            return

        with ui.dialog() as dialog, ui.card().classes("w-full max-w-6xl"):
            with ui.row().classes("w-full justify-between items-center mb-2"):
                with ui.column().classes("gap-0"):
                    ui.label(
                        t(
                            "版本对比 - {arg0} -> {arg1}",
                            arg0=result["previous_version"],
                            arg1=result["version"],
                        )
                    ).classes("text-lg font-semibold app-text-primary")
                    ui.label(f"{tool['project']} / {tool['name']}").classes(
                        "text-sm text-gray-500"
                    )
                ui.button(icon="close", on_click=dialog.close).props("flat round dense")

            with ui.scroll_area().classes("w-full h-[70vh] border border-gray-100"):
                ui.code(result.get("diff", ""), language="diff").classes("w-full")

        dialog.open()

    def confirm_rollback(
        self, tool: dict[str, Any], version: dict[str, Any], parent_dialog
    ):
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-md"):
            ui.label(t("确认回滚")).classes("text-lg font-semibold mb-2")
            ui.label(
                t(
                    "将 {arg0} 回滚到 {arg1}。",
                    arg0=tool["display_name"],
                    arg1=version["version"],
                )
            ).classes("text-gray-700")
            ui.label(t("系统会把该内容保存为新的当前版本。")).classes(
                "text-sm text-gray-500 mt-1"
            )

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button(t("取消"), on_click=dialog.close).props("flat")
                ui.button(
                    t("确认回滚"),
                    icon="settings_backup_restore",
                    on_click=lambda: self.rollback_version(
                        tool,
                        version,
                        dialog,
                        parent_dialog,
                    ),
                ).props("color=warning")

        dialog.open()

    def rollback_version(
        self,
        tool: dict[str, Any],
        version: dict[str, Any],
        dialog,
        parent_dialog,
    ):
        result = admin_tool_service.rollback_tool_to_version(tool["id"], version["id"])
        if not result.get("success"):
            ui.notify(result.get("error", "回滚失败"), type="negative")
            return

        ui.notify(
            t(
                "已回滚到 {arg0}，新版本 {arg1}",
                arg0=result.get("source_version"),
                arg1=result.get("version"),
            ),
            type="positive",
        )
        dialog.close()
        parent_dialog.close()
        self.refresh_data(silent=True)


tool_management_controller = ToolManagementController()
