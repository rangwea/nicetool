"""
工具管理服务

提供工具的管理操作：
- 列出工具（按项目过滤）
- 获取工具详情和内容
- 删除工具
- 获取所有项目名称
"""

import os
from dataclasses import dataclass
from typing import Any

from core.logger import get_logger
from core.settings import settings
from core.tool_identity import validate_project_name, validate_tool_identity
from service.tool_metadata import parse_tool_metadata
from service.tool_storage import get_tool_storage, restore_all_current_tools

logger = get_logger(__name__)


@dataclass
class ToolMeta:
    """工具元数据"""

    project: str  # 所属项目（目录名）
    name: str  # 工具名（文件名，不含 .py）
    title: str  # 工具标题（从 docstring 的 name 字段）
    description: str  # 工具描述
    creator: str  # 创建者
    created_at: str  # 创建时间
    updated_at: str  # 更新时间
    path: str  # 相对路径
    tags: str = ""  # 工具标签，逗号分隔

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "creator": self.creator,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "path": self.path,
            "tags": self.tags,
        }


def _get_tools_base_dir() -> str:
    """获取 tools 基础目录的绝对路径"""
    return os.path.abspath(settings.get_tools_dir())


def _parse_tool_meta(filepath: str, project: str, tool_name: str) -> ToolMeta | None:
    """从文件中解析工具元数据"""
    try:
        content = _read_tool_file(filepath)

        metadata = parse_tool_metadata(content)

        # 默认值
        title = tool_name
        description = ""
        creator = ""
        created_at = ""
        updated_at = ""
        tags = ""

        if metadata:
            title = metadata.get("name", tool_name)
            description = metadata.get("description", "")
            creator = metadata.get("creator", "")
            created_at = metadata.get("created_at", "")
            updated_at = metadata.get("updated_at", "")
            tags = metadata.get("tags", "")

        # 计算相对路径
        tools_dir = _get_tools_base_dir()
        rel_path = os.path.relpath(filepath, os.path.dirname(tools_dir))

        return ToolMeta(
            project=project,
            name=tool_name,
            title=title,
            description=description,
            creator=creator,
            created_at=created_at,
            updated_at=updated_at,
            path=rel_path,
            tags=tags,
        )

    except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        logger.error(f"解析工具元数据失败 {filepath}: {e}")
        return None


def _read_tool_file(filepath: str) -> str:
    """读取工具文件内容。"""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def _ensure_tool_file(project: str, tool_name: str) -> str | None:
    """确保本地运行缓存存在，缺失时从正式存储恢复。"""
    filepath = os.path.join(_get_tools_base_dir(), project, f"{tool_name}.py")
    if os.path.exists(filepath):
        return filepath

    restored_path = get_tool_storage().restore_current_to_local(project, tool_name)
    return restored_path if restored_path and os.path.exists(restored_path) else None


# ============================================================================
# 公开 API
# ============================================================================


def list_tool_projects() -> list[str]:
    """
    获取所有项目名称（即 tools 目录下的子目录名）

    Returns:
        项目名称列表
    """
    tools_dir = _get_tools_base_dir()

    if not os.path.exists(tools_dir):
        logger.warning(f"工具目录不存在: {tools_dir}")
        restore_all_current_tools()

    projects = []
    if not os.path.exists(tools_dir):
        return projects

    for item in os.listdir(tools_dir):
        item_path = os.path.join(tools_dir, item)
        if os.path.isdir(item_path) and not item.startswith("_"):
            projects.append(item)

    return sorted(projects)


def list_tools(project: str | None = None) -> list[dict[str, Any]]:
    """
    列出所有工具

    Args:
        project: 可选，按项目过滤

    Returns:
        工具元数据列表
    """
    if project is not None:
        validate_project_name(project)

    tools_dir = _get_tools_base_dir()

    if not os.path.exists(tools_dir):
        logger.warning(f"工具目录不存在: {tools_dir}")
        restore_all_current_tools()

    if not os.path.exists(tools_dir):
        return []

    tools = []

    # 确定要扫描的项目目录
    if project:
        project_dirs = (
            [project] if os.path.isdir(os.path.join(tools_dir, project)) else []
        )
    else:
        project_dirs = [
            d
            for d in os.listdir(tools_dir)
            if os.path.isdir(os.path.join(tools_dir, d)) and not d.startswith("_")
        ]

    for project_name in project_dirs:
        project_path = os.path.join(tools_dir, project_name)

        for filename in os.listdir(project_path):
            if filename.endswith(".py") and filename != "__init__.py":
                filepath = os.path.join(project_path, filename)
                tool_name = filename[:-3]  # 去掉 .py

                meta = _parse_tool_meta(filepath, project_name, tool_name)
                if meta:
                    tools.append(meta.to_dict())

    return tools


def get_tool(
    project: str, tool_name: str, include_content: bool = False
) -> dict[str, Any] | None:
    """
    获取工具详情

    Args:
        project: 所属项目
        tool_name: 工具名称
        include_content: 是否包含代码内容

    Returns:
        工具信息字典，不存在返回 None
    """
    validate_tool_identity(project, tool_name)

    tools_dir = _get_tools_base_dir()
    filepath = os.path.join(tools_dir, project, f"{tool_name}.py")

    if not os.path.exists(filepath):
        filepath = _ensure_tool_file(project, tool_name)
        if not filepath:
            return None

    meta = _parse_tool_meta(filepath, project, tool_name)
    if not meta:
        return None

    result = {"meta": meta.to_dict()}

    if include_content:
        try:
            result["content"] = _read_tool_file(filepath)
        except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            logger.error(f"读取工具内容失败 {filepath}: {e}")
            result["content"] = None

    return result


def delete_tool(project: str, tool_name: str) -> dict[str, Any]:
    """
    删除工具

    Args:
        project: 所属项目
        tool_name: 工具名称

    Returns:
        {"success": True} 或 {"success": False, "error": "..."}
    """
    validate_tool_identity(project, tool_name)

    tools_dir = _get_tools_base_dir()
    filepath = os.path.join(tools_dir, project, f"{tool_name}.py")

    # 检查是否存在
    if not os.path.exists(filepath):
        filepath = _ensure_tool_file(project, tool_name)
        if not filepath:
            return {"success": False, "error": f"工具不存在: {project}/{tool_name}"}

    try:
        if not get_tool_storage().delete_tool(project, tool_name):
            return {"success": False, "error": "工具存储删除失败，本地缓存未删除"}
        if os.path.exists(filepath):
            os.remove(filepath)
        logger.info(f"删除工具成功: {project}/{tool_name}")
        return {"success": True}

    except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        logger.error(f"删除工具失败 {project}/{tool_name}: {e}")
        return {"success": False, "error": f"删除文件失败: {e}"}
