import os
from collections.abc import Callable
from typing import Any

from core.logger import get_logger, get_tool_logger
from core.settings import settings
from core.tool_identity import validate_tool_identity
from service.tool_runtime import load_tool_entrypoint

# 获取日志器
logger = get_logger(__name__)


class ToolLoadError(RuntimeError):
    """工具源码存在但无法加载。"""


def load_and_execute_project_tool(
    project_name: str, tool_name: str
) -> tuple[Callable[..., Any], bool]:
    """动态加载并执行指定项目的工具"""
    validate_tool_identity(project_name, tool_name)
    tool_logger = get_tool_logger(project_name, tool_name)
    filepath = os.path.join(
        os.path.abspath(settings.get_tools_dir()), project_name, f"{tool_name}.py"
    )
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"工具不存在: {project_name}/{tool_name}")
    try:
        return load_tool_entrypoint(f"tools_{project_name}_{tool_name}", filepath)
    except Exception as exc:
        tool_logger.exception("工具模块加载失败")
        raise ToolLoadError(
            f"工具加载失败: {project_name}/{tool_name} - {exc}"
        ) from exc


def get_tool_by_name(
    tool_name: str, project_name: str | None = None
) -> dict[str, Any] | None:
    """根据名称获取工具信息"""
    try:
        from service.tool_manage_service import list_tools

        tools = list_tools(project=project_name)

        for tool in tools:
            if tool.get("name") == tool_name and (
                project_name is None or tool.get("project") == project_name
            ):
                return tool

        return None

    except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        logger.error(f"获取工具信息失败: {e}")
        return None
