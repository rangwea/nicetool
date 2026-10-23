from nicegui import ui

from component.auth_user import render_current_user
from component.brand import render_brand_logo
from component.language import localized_page
from component.tool_shell import BORDER_SUBTLE, PLATFORM_SIDEBAR
from core.error_handler import handle_service_errors
from core.i18n import t
from core.logger import get_logger

from .datasource import datasource_controller
from .enum_management import enum_management_controller
from .nicetool_environment import nicetool_environment_controller
from .preview_log import preview_log_controller
from .tool_management import tool_management_controller
from .user_management import user_management_controller
from .variable_management import variable_management_controller

# 获取日志器
logger = get_logger(__name__)

# 自动收集所有控制器实例
controllers = [
    user_management_controller,
    datasource_controller,
    tool_management_controller,
    enum_management_controller,
    variable_management_controller,
    nicetool_environment_controller,
    preview_log_controller,
]

# 构建菜单项
menu_items = []
for controller in controllers:
    menu = controller.menu()
    menu_items.append(
        {
            "id": controller.__class__.__name__.lower().replace("controller", ""),
            "icon": menu.icon,
            "label": menu.label,
            "color": menu.color,
            "controller": controller,
        }
    )


@localized_page("/admin")
@handle_service_errors("管理员页面加载失败")
def admin():
    """管理员首页 - 企业级左右菜单布局"""
    # 设置页面标题
    ui.page_title(t("管理员控制台 - 小工具管理平台"))

    # 页面状态
    current_page = {"value": menu_items[0]["id"]}

    def render_error_page(page_name: str, error_message: str, page_icon: str = "error"):
        """渲染美观的错误页面"""
        with ui.column().classes("w-full items-center justify-center py-12"):
            with (
                ui.card().classes("w-full max-w-2xl").props("flat"),
                ui.card_section().classes("w-full px-5 py-5"),
                ui.column().classes("w-full items-center text-center gap-3"),
            ):
                with ui.row().classes("items-center justify-center"):
                    ui.icon("error_outline").classes("text-4xl text-negative")

                ui.label(t("{arg0} 页面加载失败", arg0=page_name)).classes(
                    "text-lg font-semibold text-gray-900"
                )
                ui.label(t("抱歉，页面在加载过程中遇到了问题")).classes(
                    "text-sm text-gray-500"
                )

                with ui.column().classes(
                    "w-full gap-1 bg-gray-50 rounded-lg px-3 py-2"
                ):
                    ui.label(t("错误详情")).classes(
                        "text-sm font-semibold text-gray-800"
                    )
                    with ui.scroll_area().classes("w-full max-h-32"):
                        ui.label(error_message).classes(
                            "text-sm text-gray-700 font-mono break-all"
                        )

                with ui.row().classes("gap-2 mt-2 flex-wrap justify-center"):
                    ui.button(
                        t("刷新页面"),
                        on_click=lambda: content_area.refresh(),
                    ).props("color=primary dense")

                    ui.button(
                        t("返回首页"),
                        on_click=lambda: switch_page("settings"),
                    ).props("color=grey-7 outline dense")

                    ui.button(
                        t("复制错误信息"),
                        on_click=lambda: ui.notify(
                            t("错误信息已复制"), type="positive"
                        ),
                    ).props("flat dense color=grey-7")

            ui.label(t("如果问题持续存在，请联系系统管理员并提供错误详情")).classes(
                "text-xs text-gray-500 mt-3"
            )

    def switch_page(page_id: str):
        current_page["value"] = page_id
        content_area.refresh()
        # 更新菜单样式
        refresh_menu()

    # 主布局：左侧菜单 + 右侧内容
    with ui.row().classes("w-full h-screen overflow-hidden bg-gray-50"):
        # 左侧菜单 - 企业级侧边栏设计
        with ui.column().classes(f"w-56 h-screen flex flex-col {PLATFORM_SIDEBAR}"):
            # 侧边栏头部
            with ui.row().classes(
                f"w-full px-4 py-3 border-b {BORDER_SUBTLE} items-center"
            ):
                render_brand_logo(size_class="w-8 h-8", text_class="text-base")

            @ui.refreshable
            def menu_section():
                with ui.column().classes(
                    "w-full px-2 py-1.5 gap-0 flex-1 overflow-y-auto"
                ):
                    for item in menu_items:
                        is_active = item["id"] == current_page["value"]

                        menu_classes = (
                            "w-full items-center flex-nowrap gap-2 px-2.5 py-2.5 rounded-md "
                            "cursor-pointer transition-colors duration-150 mb-0.5 "
                            + ("app-menu-active" if is_active else "app-menu-hover")
                        )

                        with (
                            ui.row()
                            .classes(menu_classes)
                            .on(
                                "click",
                                lambda _, page_id=item["id"]: switch_page(page_id),
                            )
                        ):
                            icon_color = (
                                "text-gray-800" if is_active else "text-gray-500"
                            )
                            ui.icon(item["icon"]).classes(
                                f"text-base shrink-0 {icon_color}"
                            )

                            label_color = (
                                "text-gray-800" if is_active else "text-gray-700"
                            )
                            ui.label(t(item["label"])).classes(
                                f"min-w-0 flex-1 truncate font-medium text-sm leading-5 {label_color}"
                            )

                            # 右侧指示器（仅活跃状态显示）
                            if is_active:
                                ui.icon("chevron_right").classes(
                                    "text-xs text-gray-800 shrink-0"
                                )

            def refresh_menu():
                menu_section.refresh()

            menu_section()

            # 快速操作区域
            with (
                ui.column().classes(
                    "w-full px-2 py-2 border-t border-gray-100 flex-shrink-0"
                ),
                ui.row().classes("w-full gap-2"),
            ):
                ui.button(
                    t("用户首页"),
                    icon="home",
                    on_click=lambda: ui.navigate.to("/user"),
                ).classes(
                    "flex-1 bg-gray-50 text-gray-700 text-xs hover:bg-gray-100 whitespace-nowrap"
                ).props("size=sm flat no-wrap")

                ui.button(
                    t("AI聊天"),
                    icon="chat",
                    on_click=lambda: ui.navigate.to("/chainlit", new_tab=True),
                ).classes(
                    "flex-1 bg-blue-50 text-blue-700 text-xs hover:bg-blue-100 whitespace-nowrap"
                ).props("size=sm flat no-wrap")

            # 底部用户信息区域
            with (
                ui.row().classes(
                    "w-full px-2 py-2 border-t border-gray-100 flex-shrink-0"
                ),
                ui.row().classes("w-full items-center justify-between"),
            ):
                render_current_user()

        # 右侧内容区域
        with ui.column().classes("flex-1 bg-gray-50 h-screen overflow-y-auto"):

            @ui.refreshable
            def content_area():
                page = current_page["value"]

                # 内容容器
                with ui.column().classes(
                    "w-full max-w-screen-2xl mx-auto px-4 sm:px-6 py-5"
                ):
                    # 根据控制器来渲染对应页面
                    for item in menu_items:
                        if item["id"] == page:
                            try:
                                item["controller"].render()
                            except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                                logger.error(f"渲染{item['label']}页面失败: {e}")
                                # 显示美观的错误界面
                                render_error_page(item["label"], str(e), item["icon"])
                            break

            content_area()
