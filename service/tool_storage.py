"""使用 MySQL 保存 Tool 内容，本地 tools/ 目录仅作为运行缓存。"""

import hashlib
import os
import re
from datetime import datetime
from typing import Any

from sqlmodel import select

from core.database import db_manager
from core.logger import get_logger
from core.settings import settings
from core.tool_identity import validate_tool_identity
from models.tool import Tool, ToolVersion
from service.tool_metadata import parse_tool_metadata

logger = get_logger(__name__)


class ToolStorage:
    """使用 MySQL LONGTEXT 保存工具源码版本。"""

    def save_current(
        self,
        project: str,
        tool_name: str,
        content: str,
        created_by: str = "system",
    ) -> dict[str, Any]:
        if not db_manager:
            return {"success": False, "error": "数据库连接不可用"}

        validate_tool_identity(project, tool_name)
        filename = _filename_for(tool_name)
        content_sha256 = _sha256(content)
        now = datetime.now()

        try:
            with db_manager.session_scope() as session:
                tool = _ensure_tool_record(
                    session,
                    project,
                    filename,
                    content,
                    now,
                )
                version = _next_version(session, tool.id)
                tool_version = ToolVersion(
                    tool_id=tool.id,
                    version=version,
                    content=content,
                    content_sha256=content_sha256,
                    content_size=len(content.encode("utf-8")),
                    status="published",
                    created_by=created_by,
                    created_at=now,
                    published_at=now,
                )
                session.add(tool_version)
                tool.current_version = version
                tool.published_at = now
                tool.updated_at = now
                session.add(tool)

                logger.info(f"工具版本已保存到 MySQL: {project}/{filename}@{version}")
                return {
                    "success": True,
                    "version": version,
                    "content_sha256": content_sha256,
                    "content_size": tool_version.content_size,
                }
        except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            logger.error(f"保存工具版本失败 {project}/{filename}: {e}")
            return {"success": False, "error": str(e)}

    def load_current(self, project: str, tool_name: str) -> str | None:
        if not db_manager:
            return None

        validate_tool_identity(project, tool_name)
        filename = _filename_for(tool_name)
        try:
            with db_manager.session_scope() as session:
                statement = select(Tool).where(
                    Tool.project == project,
                    Tool.filename == filename,
                )
                tool = session.exec(statement).first()
                if not tool:
                    return None

                statement = (
                    select(ToolVersion)
                    .where(ToolVersion.tool_id == tool.id)
                    .where(ToolVersion.status == "published")
                )
                if tool and tool.current_version:
                    statement = statement.where(
                        ToolVersion.version == tool.current_version
                    )
                statement = statement.order_by(ToolVersion.published_at.desc())

                version = session.exec(statement).first()
                return version.content if version else None
        except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            logger.error(f"读取当前工具版本失败 {project}/{filename}: {e}")
            return None

    def restore_current_to_local(self, project: str, tool_name: str) -> str | None:
        content = self.load_current(project, tool_name)
        if content is None:
            return None

        filepath = _local_tool_path(project, tool_name)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath

    def restore_all_current_to_local(self) -> dict[str, Any]:
        if not db_manager:
            return {"success": False, "restored": 0, "errors": ["数据库连接不可用"]}

        restored = 0
        errors: list[str] = []
        tools: list[tuple[str, str]] = []

        try:
            with db_manager.session_scope() as session:
                statement = select(Tool).where(Tool.current_version.is_not(None))
                for tool in session.exec(statement).all():
                    tools.append((tool.project, tool.filename[:-3]))
        except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            logger.error(f"加载待恢复工具列表失败: {e}")
            return {"success": False, "restored": 0, "errors": [str(e)]}

        for project, tool_name in tools:
            try:
                filepath = self.restore_current_to_local(project, tool_name)
                if filepath:
                    restored += 1
            except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
                message = f"{project}/{tool_name}: {e}"
                logger.error(f"恢复工具缓存失败 {message}")
                errors.append(message)

        return {"success": not errors, "restored": restored, "errors": errors}

    def delete_tool(self, project: str, tool_name: str) -> bool:
        if not db_manager:
            return False

        validate_tool_identity(project, tool_name)
        filename = _filename_for(tool_name)
        now = datetime.now()
        try:
            with db_manager.session_scope() as session:
                tool_statement = select(Tool).where(
                    Tool.project == project,
                    Tool.filename == filename,
                )
                tool = session.exec(tool_statement).first()
                if not tool:
                    return False
                statement = (
                    select(ToolVersion)
                    .where(ToolVersion.tool_id == tool.id)
                    .where(ToolVersion.status == "published")
                )
                for version in session.exec(statement).all():
                    version.status = "deleted"
                    version.deleted_at = now
                    session.add(version)

                tool.current_version = None
                tool.updated_at = now
                session.add(tool)

            logger.info(f"工具存储已标记删除: {project}/{filename}")
            return True
        except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
            logger.error(f"删除工具存储失败 {project}/{filename}: {e}")
            return False


def get_tool_storage() -> ToolStorage:
    """获取 MySQL 工具存储。"""
    return ToolStorage()


def restore_all_current_tools() -> dict[str, Any]:
    """恢复所有当前工具到本地运行缓存。"""
    return get_tool_storage().restore_all_current_to_local()


def delete_tool_from_db(project: str, filename: str) -> bool:
    """从 Tool 表删除单个工具索引记录。"""
    if not db_manager:
        logger.warning("数据库连接不可用，跳过 DB 删除")
        return False

    try:
        with db_manager.session_scope() as session:
            statement = select(Tool).where(
                Tool.project == project,
                Tool.filename == filename,
            )
            tool = session.exec(statement).first()
            if tool:
                session.delete(tool)
                logger.info(f"工具 DB 记录已删除: {project}/{filename}")
            else:
                logger.debug(
                    f"delete_tool_from_db: Tool 记录不存在，跳过: {project}/{filename}"
                )
        return True
    except Exception as e:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        logger.error(f"delete_tool_from_db 失败 {project}/{filename}: {e}")
        return False


def _ensure_tool_record(
    session,
    project: str,
    filename: str,
    content: str,
    now: datetime,
) -> Tool:
    statement = select(Tool).where(
        Tool.project == project,
        Tool.filename == filename,
    )
    tool = session.exec(statement).first()
    try:
        metadata = parse_tool_metadata(content)
    except (SyntaxError, ValueError, TypeError):
        metadata = {}

    if not tool:
        tool = Tool(
            project=project,
            filename=filename,
            display_name=metadata.get("name", filename[:-3]),
            description=metadata.get("description") or None,
            creator=metadata.get("creator") or None,
            tags=metadata.get("tags") or None,
            created_at=now,
            updated_at=now,
        )
    else:
        tool.display_name = metadata.get("name", tool.display_name)
        tool.description = metadata.get("description") or tool.description
        tool.creator = metadata.get("creator") or tool.creator
        tool.tags = metadata.get("tags") or tool.tags
        tool.updated_at = now

    session.add(tool)
    session.flush()
    return tool


def _next_version(session, tool_id: int) -> str:
    statement = select(ToolVersion).where(ToolVersion.tool_id == tool_id)
    max_version = 0
    for version in session.exec(statement).all():
        match = re.fullmatch(r"v(\d+)", version.version or "")
        if match:
            max_version = max(max_version, int(match.group(1)))
    return f"v{max_version + 1}"


def _filename_for(tool_name: str) -> str:
    return f"{tool_name}.py"


def _local_tool_path(project: str, tool_name: str) -> str:
    validate_tool_identity(project, tool_name)
    return os.path.join(
        os.path.abspath(settings.get_tools_dir()),
        project,
        _filename_for(tool_name),
    )


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
