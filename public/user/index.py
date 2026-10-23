from fastapi import Request
from nicegui import app, ui

from component.auth_user import render_current_user
from component.brand import render_brand_logo
from component.language import localized_page
from component.tool_shell import (
    SURFACE_CARD,
    TOOL_SHELL_CONTENT,
    TOOL_SHELL_HEADER_BAR,
    TOOL_SHELL_HEADER_INNER,
)
from core.auth.dependencies import current_user
from core.error_handler import handle_service_errors
from core.i18n import html_t, t
from core.logger import get_logger
from service.access_control_service import filter_tools_for_user
from service.tool_manage_service import list_tools

logger = get_logger(__name__)

_PAGE_OUTER = "w-full min-h-screen flex flex-col bg-gray-50"
_HEADER_BAR = TOOL_SHELL_HEADER_BAR
_HEADER_INNER = TOOL_SHELL_HEADER_INNER
_BODY_SCROLL = "flex-1 w-full overflow-y-auto"
_INPUT_PROPS = "outlined dense color=primary clearable"
# 工具卡片：比 SURFACE_CARD 更浅的描边；标签/meta 单独样式
_TOOL_CARD = (
    "!border !border-gray-100 shadow-none hover:shadow-sm hover:-translate-y-0.5 "
    "transition-all duration-150 overflow-hidden"
)
_PROJECT_TONES = [
    "bg-blue-50 text-blue-700 border-blue-100",
    "bg-violet-50 text-violet-700 border-violet-100",
    "bg-emerald-50 text-emerald-700 border-emerald-100",
    "bg-amber-50 text-amber-700 border-amber-100",
    "bg-rose-50 text-rose-700 border-rose-100",
    "bg-cyan-50 text-cyan-700 border-cyan-100",
]
_TOOL_META_DIVIDER = "border-t border-gray-50"


@localized_page("/user")
@handle_service_errors("用户页面加载失败")
def user_dashboard(request: Request):
    """用户首页 - 浏览和使用工具"""
    ui.page_title(t("工具中心 - NiceTool"))

    logger.debug("加载工具和项目数据")
    try:
        tools_data = filter_tools_for_user(list_tools(), current_user(request))
    except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        logger.error(f"获取工具列表失败: {e}")
        ui.notify(t("获取工具列表失败"), type="negative")
        tools_data = []

    project_names = sorted({t.get("project", "未分组") for t in tools_data})
    logger.info(f"加载到 {len(tools_data)} 个工具，{len(project_names)} 个项目")

    project_options = {"全部": t("全部"), **{name: name for name in project_names}}
    all_tags = sorted(
        {
            tag.strip()
            for t in tools_data
            for tag in (t.get("tags") or "").split(",")
            if tag.strip()
        }
    )

    selected_project = {"value": "全部"}
    selected_tags: dict[str, list] = {"value": []}
    saved_view = app.storage.user.get("tool_center_view", "panel")
    view_mode = {"value": saved_view if saved_view in {"panel", "table"} else "panel"}

    with ui.column().classes(_PAGE_OUTER):
        _render_page_header()

        with ui.column().classes(_BODY_SCROLL), ui.column().classes(TOOL_SHELL_CONTENT):
            _render_page_intro(len(tools_data), len(project_names))

            search = (
                ui.input(placeholder=t("搜索名称或描述"))
                .props(_INPUT_PROPS)
                .classes("w-full")
            )

            @ui.refreshable
            def render_tools():
                filtered = _filter_tools(
                    tools_data,
                    (search.value or "").strip().lower(),
                    selected_project["value"],
                    selected_tags["value"],
                )
                if not filtered:
                    _render_empty_state()
                    return

                if view_mode["value"] == "table":
                    _render_tool_table(filtered)
                    return

                grouped: dict[str, list] = {}
                for tool in filtered:
                    key = tool.get("project", "未分组")
                    grouped.setdefault(key, []).append(tool)

                with ui.column().classes("w-full gap-5 pt-4"):
                    for project_name, project_tools in sorted(grouped.items()):
                        _render_project_section(project_name, project_tools)

            def on_project_change(e) -> None:
                selected_project["value"] = e.value
                render_tools.refresh()

            def on_tag_change(e) -> None:
                selected_tags["value"] = e.value or []
                render_tools.refresh()

            def set_view(mode: str) -> None:
                view_mode["value"] = mode
                app.storage.user["tool_center_view"] = mode
                render_filters.refresh()
                render_tools.refresh()

            @ui.refreshable
            def render_filters():
                with (
                    ui.card().classes(f"w-full {SURFACE_CARD}"),
                    ui.card_section().classes("w-full py-2 px-3"),
                    ui.row().classes("w-full gap-2 items-end flex-wrap"),
                ):
                    ui.select(
                        options=project_options,
                        label=t("项目"),
                        value=selected_project["value"],
                        on_change=on_project_change,
                    ).props(_INPUT_PROPS).classes("min-w-[10rem] flex-1")

                    if all_tags:
                        ui.select(
                            options=all_tags,
                            label=t("标签"),
                            value=selected_tags["value"],
                            multiple=True,
                            on_change=on_tag_change,
                        ).props(f"{_INPUT_PROPS} use-chips").classes(
                            "min-w-[12rem] flex-1"
                        )

                    with ui.row().classes(
                        "gap-0.5 ml-auto shrink-0 rounded-lg bg-gray-100 p-0.5"
                    ):
                        for mode, label, icon in (
                            ("panel", "面板", "grid_view"),
                            ("table", "表格", "table_rows"),
                        ):
                            active = view_mode["value"] == mode
                            ui.button(
                                t(label),
                                icon=icon,
                                on_click=lambda _, value=mode: set_view(value),
                            ).props(
                                "dense no-caps unelevated "
                                + ("color=primary" if active else "flat color=grey-7")
                            ).classes("px-2")

            search.on("change", lambda _: render_tools.refresh())
            render_filters()
            render_tools()


def _render_page_header() -> None:
    with ui.row().classes(_HEADER_BAR), ui.row().classes(_HEADER_INNER):
        with (
            ui.row()
            .classes(
                "items-center gap-2.5 min-w-0 cursor-pointer hover:opacity-80 "
                "transition-opacity"
            )
            .on("click", lambda: ui.navigate.to("/"))
        ):
            render_brand_logo()
        with ui.row().classes("items-center shrink-0"):
            render_current_user()


def _render_page_intro(tool_count: int, project_count: int) -> None:
    with ui.row().classes("w-full justify-between items-end gap-3 mb-1"):
        with ui.column().classes("gap-0"):
            ui.label(t("浏览工具")).classes("text-xl font-semibold app-text-primary")
            ui.label(t("按项目与标签筛选，点击卡片打开工具")).classes(
                "text-sm text-gray-500"
            )
        with ui.row().classes("gap-2 shrink-0"):
            ui.badge(t("{arg0} 个工具", arg0=tool_count)).props("color=primary outline")
            ui.badge(t("{arg0} 个项目", arg0=project_count)).props("color=grey-4")


def _filter_tools(
    tools_data: list,
    query: str,
    selected_project: str,
    active_tags: list,
) -> list:
    def match_tool(t: dict) -> bool:
        if selected_project != "全部" and t.get("project") != selected_project:
            return False
        if query:
            name = _tool_display_name(t).lower()
            identifier = (t.get("name") or "").lower()
            desc = (t.get("description") or "").lower()
            if query not in name and query not in identifier and query not in desc:
                return False
        if active_tags:
            tool_tags = {
                tag.strip().lower()
                for tag in (t.get("tags") or "").split(",")
                if tag.strip()
            }
            if not all(tag.lower() in tool_tags for tag in active_tags):
                return False
        return True

    return [t for t in tools_data if match_tool(t)]


def _render_empty_state() -> None:
    with ui.column().classes("w-full items-center py-16 gap-2"):
        ui.icon("inbox").classes("text-4xl text-gray-300")
        ui.label(t("未找到匹配的工具")).classes("text-sm text-gray-500")
        ui.label(t("尝试调整搜索或筛选条件")).classes("text-xs text-gray-400")


def _render_project_section(
    project_name: str,
    project_tools: list,
) -> None:
    with ui.row().classes("w-full items-center justify-between"):
        project_tone = _project_tone(project_name)
        ui.label(project_name).classes(
            f"text-sm font-semibold px-2 py-1 rounded-md border {project_tone}"
        )
        ui.label(t("{arg0} 个", arg0=len(project_tools))).classes(
            "text-xs text-gray-500"
        )

    with ui.element("div").classes(
        "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 w-full"
    ):
        for tool in project_tools:
            _render_tool_card(tool)


def _render_tool_tag(label: str, project_name: str) -> None:
    project_tone = _project_tone(project_name)
    ui.label(label).classes(
        f"text-xs font-medium px-2 py-0.5 rounded-md border {project_tone}"
    )


def _render_tool_card(tool: dict) -> None:
    display_name = _tool_display_name(tool)
    description = tool.get("description") or "暂无描述"
    tool_tags = _parse_tags(tool)
    project_name = tool.get("project") or "未分组"

    with (
        ui.card()
        .classes(f"w-full cursor-pointer {_TOOL_CARD}")
        .props("flat")
        .on("click", lambda t=tool: use_tool(t)),
        ui.card_section().classes("py-3 px-4 flex flex-col gap-2 h-full"),
    ):
        with ui.row().classes("w-full justify-between items-start gap-2"):
            ui.label(display_name).classes(
                "text-base font-semibold app-text-primary truncate flex-1"
            )
            ui.icon("chevron_right").classes("text-gray-400 shrink-0")
        ui.label(description).classes(
            "text-sm text-gray-600 line-clamp-2 min-h-[2.5rem]"
        )
        if tool_tags:
            with ui.row().classes("gap-1 flex-wrap"):
                for tag in tool_tags[:3]:
                    _render_tool_tag(tag, project_name)
                if len(tool_tags) > 3:
                    _render_tool_tag(f"+{len(tool_tags) - 3}", project_name)
        meta = _tool_meta_line(tool)
        if meta:
            ui.label(meta).classes(
                f"text-xs text-gray-500 pt-2 mt-1 {_TOOL_META_DIVIDER}"
            )


def _render_tool_table(tools: list[dict]) -> None:
    columns = [
        {
            "name": "name",
            "label": t("工具"),
            "field": "name",
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
        {"name": "meta", "label": t("维护信息"), "field": "meta", "align": "left"},
        {"name": "actions", "label": t("操作"), "field": "actions", "align": "right"},
    ]
    rows = [
        {
            "id": f"{tool.get('project', '')}/{tool.get('name', '')}",
            "name": _tool_display_name(tool),
            "project": tool.get("project") or "未分组",
            "description": tool.get("description") or "暂无描述",
            "tags": " · ".join(_parse_tags(tool)) or "—",
            "meta": _tool_meta_line(tool) or "—",
            "tool": tool,
        }
        for tool in tools
    ]
    table = (
        ui.table(
            columns=columns,
            rows=rows,
            row_key="id",
            pagination={"rowsPerPage": 15},
        )
        .classes("w-full mt-4 overflow-hidden")
        .props("flat dense separator=horizontal color=primary")
    )
    table.add_slot(
        "body-cell-project",
        """
        <q-td :props="props">
            <q-badge color="blue-grey-1" text-color="blue-grey-8" :label="props.value" />
        </q-td>
        """,
    )
    table.add_slot(
        "body-cell-description",
        """
        <q-td :props="props">
            <div class="ellipsis" style="max-width: 32rem">{{ props.value }}</div>
            <q-tooltip>{{ props.value }}</q-tooltip>
        </q-td>
        """,
    )
    table.add_slot(
        "body-cell-actions",
        html_t("""
        <q-td :props="props">
            <q-btn flat dense round color="primary" icon="arrow_forward" @click="$parent.$emit('open', props.row)">
                <q-tooltip>打开工具</q-tooltip>
            </q-btn>
        </q-td>
        """),
    )
    table.on("open", lambda event: use_tool(event.args["tool"]))


def _project_tone(project_name: str) -> str:
    index = sum(ord(char) for char in project_name) % len(_PROJECT_TONES)
    return _PROJECT_TONES[index]


def _parse_tags(tool: dict) -> list[str]:
    return [tag.strip() for tag in (tool.get("tags") or "").split(",") if tag.strip()]


def _tool_meta_line(tool: dict) -> str:
    parts: list[str] = []
    if tool.get("creator"):
        parts.append(tool["creator"])
    if tool.get("created_at"):
        parts.append(str(tool["created_at"]))
    return " · ".join(parts)


def _tool_display_name(tool: dict) -> str:
    return tool.get("title") or tool.get("name") or "未命名工具"


def use_tool(tool: dict) -> None:
    try:
        logger.info(f"用户使用工具: {tool.get('name')}")
        project_name = tool.get("project", "")
        tool_name = tool.get("name", "")
        if not project_name or not tool_name:
            raise ValueError("工具项目或文件标识为空")
        ui.navigate.to(f"/user/tools/{project_name}/{tool_name}")
    except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        logger.error(f"打开工具失败: {e}")
        ui.notify(t("打开工具失败: {arg0}", arg0=e), type="negative")
