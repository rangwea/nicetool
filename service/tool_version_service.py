"""Tool 版本回滚服务。"""

from typing import Any

from sqlmodel import select

from core.database import db_manager
from core.logger import get_logger
from models.tool import ToolVersion

logger = get_logger(__name__)


def rollback_tool(tool_id: int, version: str) -> dict[str, Any]:
    """将 Tool 回滚到指定版本。"""
    if not db_manager:
        return {"success": False, "error": "数据库连接不可用"}
    try:
        with db_manager.session_scope() as session:
            statement = (
                select(ToolVersion)
                .where(ToolVersion.tool_id == tool_id)
                .where(ToolVersion.version == version)
                .where(ToolVersion.status == "published")
                .order_by(ToolVersion.published_at.desc(), ToolVersion.id.desc())
            )
            version_row = session.exec(statement).first()
            if not version_row:
                return {"success": False, "error": f"版本不存在: {version}"}
            version_id = version_row.id

        from service.admin_tool_service import rollback_tool_to_version

        result = rollback_tool_to_version(tool_id, version_id)
        if result.get("success"):
            logger.info(f"回滚 Tool 成功: ID={tool_id} -> {version}")
        return result
    except Exception as exc:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        logger.error(f"回滚 Tool 失败: {exc}")
        return {"success": False, "error": str(exc)}
