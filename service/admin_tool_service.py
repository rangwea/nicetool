"""
后台工具管理服务
"""

import difflib
import os
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlmodel import select

from core.auth.actor import system_actor
from core.database import db_manager
from core.logger import get_logger
from core.settings import settings
from models.tool import Tool, ToolLifecycleEvent, ToolVersion
from service import tool_lifecycle_service
from service.tool_runtime import validate_tool_entrypoint
from service.tool_storage import get_tool_storage

logger = get_logger(__name__)

FORMAL_LIFECYCLE_ACTIONS = (
    "tool.publish",
    "tool.rollback",
    "tool.delete",
    "tool.restore_cache",
)

EVENT_ACTION_LABELS = {
    "tool.publish": ("发布版本", "发布失败"),
    "tool.rollback": ("回滚版本", "回滚失败"),
    "tool.delete": ("删除工具", "删除失败"),
    "tool.restore_cache": ("恢复运行缓存", "恢复缓存失败"),
}

ACTOR_TYPE_LABELS = {
    "user": "后台用户",
    "token": "Token",
    "system": "系统",
}


def _split_tags(tags: str | None) -> list[str]:
    return [tag.strip() for tag in (tags or "").split(",") if tag.strip()]


def _format_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _tool_name(filename: str) -> str:
    return filename.removesuffix(".py")


def _truncate_text(value: str, limit: int = 48) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def _tool_to_row(tool: Tool, versions_count: int) -> dict[str, Any]:
    tags = _split_tags(tool.tags)
    description = tool.description or ""
    return {
        "id": tool.id,
        "project": tool.project,
        "filename": tool.filename,
        "name": _tool_name(tool.filename),
        "display_name": tool.display_name or _tool_name(tool.filename),
        "description": description,
        "description_preview": _truncate_text(description),
        "creator": tool.creator or "",
        "current_version": tool.current_version or "",
        "tags": tool.tags or "",
        "tags_list": tags,
        "tags_text": ", ".join(tags),
        "versions_count": versions_count,
        "created_at": _format_datetime(tool.created_at),
        "updated_at": _format_datetime(tool.updated_at),
        "published_at": _format_datetime(tool.published_at),
    }


def list_tools(
    *,
    search: str = "",
    project: str = "all",
    tags: list[str] | None = None,
) -> list[dict[str, Any]]:
    """列出工具索引，支持名称/项目/描述检索和 tag 过滤。"""
    if not db_manager:
        return []

    tags = tags or []
    query = search.strip().lower()

    with db_manager.session_scope() as session:
        statement = select(Tool)
        if project != "all":
            statement = statement.where(Tool.project == project)
        statement = statement.order_by(Tool.updated_at.desc())
        tools = session.exec(statement).all()
        version_counts = _count_versions_by_tool(session, tools)

        rows: list[dict[str, Any]] = []
        for tool in tools:
            if query:
                haystack = " ".join(
                    [
                        tool.filename or "",
                        tool.display_name or "",
                        tool.project or "",
                        tool.description or "",
                    ]
                ).lower()
                if query not in haystack:
                    continue

            tool_tags = {tag.lower() for tag in _split_tags(tool.tags)}
            if tags and not all(tag.lower() in tool_tags for tag in tags):
                continue

            versions_count = version_counts.get(tool.id, 0)
            rows.append(_tool_to_row(tool, versions_count))

        return rows


def list_filter_options() -> dict[str, list[str]]:
    """获取项目和 tag 筛选项。"""
    if not db_manager:
        return {"projects": [], "tags": []}

    with db_manager.session_scope() as session:
        tools = session.exec(select(Tool)).all()
        projects = sorted({tool.project for tool in tools if tool.project})
        tags = sorted({tag for tool in tools for tag in _split_tags(tool.tags)})
        return {"projects": projects, "tags": tags}


def get_tool_workspace(tool_id: int) -> dict[str, Any]:
    """获取后台工具工作区所需的只读聚合数据。"""
    if not db_manager:
        return {"success": False, "error": "数据库连接不可用"}

    try:
        with db_manager.session_scope() as session:
            tool = session.get(Tool, tool_id)
            if not tool:
                return {"success": False, "error": f"工具不存在: ID={tool_id}"}

            versions = _query_tool_versions(session, tool)
            row = _tool_to_row(tool, len(versions))
            version_rows = [
                _version_to_row(version, tool.current_version, has_previous=index > 0)
                for index, version in enumerate(versions)
            ]
            event_statement = (
                select(ToolLifecycleEvent)
                .where(ToolLifecycleEvent.project == tool.project)
                .where(ToolLifecycleEvent.tool_name == _tool_name(tool.filename))
                .where(ToolLifecycleEvent.action.in_(FORMAL_LIFECYCLE_ACTIONS))
                .order_by(ToolLifecycleEvent.created_at.desc())
                .limit(20)
            )
            events = [
                _lifecycle_event_to_row(event)
                for event in session.exec(event_statement).all()
                if _is_formal_lifecycle_event(event)
            ]

        state_result = tool_lifecycle_service.get_tool_state(
            system_actor("admin-workspace-read"),
            row["project"],
            row["name"],
        )
        state = (
            state_result.data.get("state", {})
            if getattr(state_result, "success", False)
            else {}
        )
        return {
            "success": True,
            "tool": row,
            "state": state,
            "versions": list(reversed(version_rows)),
            "events": events,
        }
    except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        logger.error(f"获取工具工作区失败 tool_id={tool_id}: {e}")
        return {"success": False, "error": str(e)}


def list_tool_versions(tool_id: int) -> list[dict[str, Any]]:
    """列出工具历史版本。"""
    if not db_manager:
        return []

    with db_manager.session_scope() as session:
        tool = session.get(Tool, tool_id)
        if not tool:
            raise ValueError(f"工具不存在: ID={tool_id}")

        versions = _query_tool_versions(session, tool)
        rows = [
            _version_to_row(version, tool.current_version, has_previous=index > 0)
            for index, version in enumerate(versions)
        ]
        return list(reversed(rows))


def get_version_content(tool_id: int, version_id: int) -> dict[str, Any]:
    """获取版本代码内容。"""
    if not db_manager:
        return {"success": False, "error": "数据库连接不可用"}

    try:
        with db_manager.session_scope() as session:
            tool = session.get(Tool, tool_id)
            version = session.get(ToolVersion, version_id)
            if not tool:
                return {"success": False, "error": f"工具不存在: ID={tool_id}"}
            if not version:
                return {"success": False, "error": f"版本不存在: ID={version_id}"}
            if not _version_belongs_to_tool(tool, version):
                return {"success": False, "error": "版本不属于当前工具"}

            return {
                "success": True,
                "version": version.version,
                "content": version.content,
                "filename": tool.filename,
                "published_at": _format_datetime(version.published_at),
            }
    except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        logger.error(
            f"获取版本代码失败 tool_id={tool_id}, version_id={version_id}: {e}"
        )
        return {"success": False, "error": str(e)}


def diff_with_previous_version(tool_id: int, version_id: int) -> dict[str, Any]:
    """获取指定版本与上一版本的 unified diff。"""
    if not db_manager:
        return {"success": False, "error": "数据库连接不可用"}

    try:
        with db_manager.session_scope() as session:
            tool = session.get(Tool, tool_id)
            version = session.get(ToolVersion, version_id)
            if not tool:
                return {"success": False, "error": f"工具不存在: ID={tool_id}"}
            if not version:
                return {"success": False, "error": f"版本不存在: ID={version_id}"}
            if not _version_belongs_to_tool(tool, version):
                return {"success": False, "error": "版本不属于当前工具"}

            versions = _query_tool_versions(session, tool)
            index = next(
                (i for i, item in enumerate(versions) if item.id == version.id), -1
            )
            if index <= 0:
                return {"success": False, "error": "没有上一版本可对比"}

            previous = versions[index - 1]
            diff = "".join(
                difflib.unified_diff(
                    previous.content.splitlines(keepends=True),
                    version.content.splitlines(keepends=True),
                    fromfile=f"{previous.version}/{tool.filename}",
                    tofile=f"{version.version}/{tool.filename}",
                )
            )

            return {
                "success": True,
                "version": version.version,
                "previous_version": previous.version,
                "diff": diff or "两个版本内容一致",
            }
    except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        logger.error(f"版本对比失败 tool_id={tool_id}, version_id={version_id}: {e}")
        return {"success": False, "error": str(e)}


def rollback_tool_to_version(tool_id: int, version_id: int) -> dict[str, Any]:
    """将历史版本内容恢复为新的当前版本。"""
    if not db_manager:
        return {"success": False, "error": "数据库连接不可用"}

    try:
        with db_manager.session_scope() as session:
            tool = session.get(Tool, tool_id)
            version = session.get(ToolVersion, version_id)
            if not tool:
                return {"success": False, "error": f"工具不存在: ID={tool_id}"}
            if not version:
                return {"success": False, "error": f"版本不存在: ID={version_id}"}

            if not _version_belongs_to_tool(tool, version):
                return {"success": False, "error": "版本不属于当前工具"}

            content = version.content
            project = tool.project
            filename = tool.filename
            source_version = version.version

        validate_tool_entrypoint(content)
        filepath = os.path.join(
            os.path.abspath(settings.get_tools_dir()),
            project,
            filename,
        )

        storage_result = get_tool_storage().save_current(
            project,
            _tool_name(filename),
            content,
            created_by="rollback",
        )
        if not storage_result.get("success"):
            return {
                "success": False,
                "error": storage_result.get("error", "回滚保存失败"),
            }

        _write_tool_file_atomic(filepath, content)
        logger.info(
            "工具已回滚: "
            f"{project}/{filename} -> {source_version}, "
            f"new={storage_result.get('version')}"
        )
        return {
            "success": True,
            "version": storage_result.get("version", ""),
            "source_version": source_version,
        }
    except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        logger.error(f"工具回滚失败 tool_id={tool_id}, version_id={version_id}: {e}")
        return {"success": False, "error": str(e)}


def _lifecycle_event_to_row(event: ToolLifecycleEvent) -> dict[str, Any]:
    action_label = _event_action_label(event.action, bool(event.success))
    action_group = _event_action_group(event.action)
    actor_type_label = ACTOR_TYPE_LABELS.get(event.actor_type, event.actor_type)
    content_sha256_short = _short_sha256(event.content_sha256)
    return {
        "id": event.id,
        "project": event.project,
        "tool_name": event.tool_name,
        "action": event.action,
        "action_label": action_label,
        "action_group": action_group,
        "actor_type": event.actor_type,
        "actor_type_label": actor_type_label,
        "actor_id": event.actor_id,
        "actor_name": event.actor_name,
        "version": event.version,
        "preview_key": event.preview_key,
        "content_sha256": event.content_sha256,
        "content_sha256_short": content_sha256_short,
        "success": event.success,
        "success_label": "成功" if event.success else "失败",
        "success_color": "positive" if event.success else "negative",
        "message": event.message,
        "created_at": _format_datetime(event.created_at),
        "details": {
            "action": event.action,
            "actor_id": event.actor_id,
            "content_sha256": event.content_sha256,
            "preview_key": event.preview_key,
            "version": event.version,
        },
    }


def _is_formal_lifecycle_event(event: ToolLifecycleEvent) -> bool:
    return event.action in FORMAL_LIFECYCLE_ACTIONS


def _event_action_group(action: str) -> str:
    return action.removeprefix("tool.")


def _event_action_label(action: str, success: bool) -> str:
    labels = EVENT_ACTION_LABELS.get(action)
    if labels is None:
        return action
    success_label, failure_label = labels
    return success_label if success else failure_label


def _short_sha256(value: str | None, length: int = 12) -> str:
    return value[:length] if value else ""


def _write_tool_file_atomic(filepath: str, content: str) -> None:
    """原子替换本地运行缓存，避免回滚时留下半写入文件。"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    temp_path = f"{filepath}.tmp.{os.getpid()}"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, filepath)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def _count_versions_by_tool(session, tools: list[Tool]) -> dict[int, int]:
    """按 tool_id 批量统计版本数。"""
    counts: dict[int, int] = {}
    tools_with_id = [tool for tool in tools if tool.id is not None]
    if not tools_with_id:
        return counts

    tool_ids = [tool.id for tool in tools_with_id]
    statement = (
        select(ToolVersion.tool_id, func.count(ToolVersion.id))
        .where(ToolVersion.tool_id.in_(tool_ids))
        .group_by(ToolVersion.tool_id)
    )
    for tool_id, count in session.exec(statement).all():
        if tool_id is not None:
            counts[int(tool_id)] = int(count)

    return counts


def _version_belongs_to_tool(tool: Tool, version: ToolVersion) -> bool:
    return version.tool_id == tool.id


def _tool_versions_statement(tool: Tool):
    return select(ToolVersion).where(ToolVersion.tool_id == tool.id)


def _query_tool_versions(session, tool: Tool) -> list[ToolVersion]:
    statement = _tool_versions_statement(tool).order_by(
        ToolVersion.published_at.asc(),
        ToolVersion.id.asc(),
    )
    return session.exec(statement).all()


def _version_to_row(
    version: ToolVersion,
    current_version: str | None,
    *,
    has_previous: bool,
) -> dict[str, Any]:
    return {
        "id": version.id,
        "version": version.version,
        "status": version.status,
        "is_current": version.version == current_version
        and version.status == "published",
        "content_sha256": version.content_sha256,
        "content_size": version.content_size,
        "created_by": version.created_by,
        "has_previous": has_previous,
        "created_at": _format_datetime(version.created_at),
        "published_at": _format_datetime(version.published_at),
    }
