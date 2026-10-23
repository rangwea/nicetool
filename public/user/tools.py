from component.language import localized_page

"""
工具相关API接口和页面路由
"""

from fastapi import HTTPException, Request, status
from nicegui import ui

from component.tool_shell import render_tool_shell
from core.auth.dependencies import current_user
from core.i18n import t
from core.logger import get_logger, setup_tool_logging, tool_log_context
from service.access_control_service import can_access_project
from service.tool_service import get_tool_by_name, load_and_execute_project_tool

logger = get_logger(__name__)


@localized_page("/user/tools/{project_name}/{tool_name}")
async def tools_handler(request: Request, project_name: str, tool_name: str):
    """项目工具路由处理器"""
    logger.info(f"Loading project tool: {project_name}/{tool_name}")

    if not can_access_project(current_user(request), project_name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有该项目的访问权限",
        )

    try:
        # 动态加载项目工具
        result = load_and_execute_project_tool(project_name, tool_name)

        if result and len(result) == 2:
            tool_func, is_async = result

            # 为用户代码的标准 logging 设置文件 handler（回调场景也生效）
            module_name = f"tools_{project_name}_{tool_name}"
            setup_tool_logging(project_name, tool_name, module_name)
            # 也为 tools.{project_name}.{tool_name} 设置（exec 路径使用的模块名）
            setup_tool_logging(
                project_name, tool_name, f"tools.{project_name}.{tool_name}"
            )

            tool_meta = get_tool_by_name(tool_name, project_name) or {}
            shell_title = tool_meta.get("title") or tool_name

            with (
                render_tool_shell(
                    title=shell_title,
                    subtitle=project_name,
                    mode="tool",
                ),
                tool_log_context(project_name, tool_name),
            ):
                if is_async:
                    await tool_func()
                else:
                    tool_func()
        else:
            logger.warning(
                f"Invalid result from load_and_execute_project_tool: {result}"
            )

    except Exception as e:
        error_msg = str(e)
        with tool_log_context(project_name, tool_name):
            logger.exception(f"工具渲染失败: {project_name}/{tool_name}")

        # 根据错误类型显示不同的错误页面
        if "工具不存在" in error_msg:
            with ui.column().classes("items-center justify-center min-h-screen gap-4"):
                ui.icon("search_off", size="4rem").classes("text-gray-400")
                ui.label(t("工具不存在")).classes("text-2xl font-bold text-gray-600")
                ui.label(error_msg).classes("text-gray-500 text-center")
                ui.label(
                    t("请检查URL是否正确，或联系管理员确认工具是否已部署。")
                ).classes("text-sm text-gray-400 text-center max-w-md mt-2")

                with ui.row().classes("gap-2 mt-4"):
                    ui.button(
                        t("返回项目"),
                        on_click=lambda: ui.navigate.to("/user"),
                    ).classes("bg-blue-500 text-white")

                    ui.button(
                        t("返回用户首页"),
                        on_click=lambda: ui.navigate.to("/user"),
                    ).classes("bg-gray-500 text-white")

        elif "工具加载失败" in error_msg or "没有找到可执行的代码" in error_msg:
            with ui.column().classes("items-center justify-center min-h-screen gap-4"):
                ui.icon("warning", size="4rem").classes("text-orange-500")
                ui.label(t("工具加载失败")).classes(
                    "text-2xl font-bold text-orange-600"
                )
                ui.label(error_msg).classes("text-gray-600 text-center max-w-md")

                with ui.row().classes("gap-2 mt-4"):
                    ui.button(
                        t("返回项目"),
                        on_click=lambda: ui.navigate.to("/user"),
                    ).classes("bg-blue-500 text-white")

                    ui.button(
                        t("返回用户首页"),
                        on_click=lambda: ui.navigate.to("/user"),
                    ).classes("bg-gray-500 text-white")

        else:
            # 工具执行错误
            with ui.column().classes("items-center justify-center min-h-screen gap-4"):
                ui.icon("error", size="4rem").classes("text-red-500")
                ui.label(t("工具执行失败")).classes("text-2xl font-bold text-red-600")
                ui.label(
                    t("工具在运行过程中发生了错误，请检查工具代码或联系开发者。")
                ).classes("text-gray-600 text-center max-w-md")
                ui.label(t("技术详情: {arg0}", arg0=error_msg)).classes(
                    "text-xs text-gray-400 mt-2"
                )

                with ui.row().classes("gap-2 mt-4"):
                    ui.button(
                        t("返回项目"),
                        on_click=lambda: ui.navigate.to("/user"),
                    ).classes("bg-blue-500 text-white")

                    ui.button(
                        t("返回用户首页"),
                        on_click=lambda: ui.navigate.to("/user"),
                    ).classes("bg-gray-500 text-white")
