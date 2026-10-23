"""Unified tool lifecycle service helpers."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlmodel import select

from core.auth.actor import Actor, require_scope
from core.database import db_manager
from core.logger import get_logger
from core.tool_identity import InvalidToolIdentity, validate_tool_identity
from models.tool import Tool, ToolLifecycleEvent, ToolVersion
from service import tool_manage_service, tool_version_service
from service.preview_service import create_temporary_preview
from service.tool_runtime import ToolEntryPointError, validate_tool_entrypoint
from service.tool_storage import (
    delete_tool_from_db,
    get_tool_storage,
)

logger = get_logger(__name__)


@dataclass
class LifecycleResult:
    success: bool
    code: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.data,
            "success": self.success,
            "code": self.code,
            "message": self.message,
            "next_action": self.next_action,
        }


@dataclass(frozen=True)
class ToolIdentity:
    id: int
    project: str
    filename: str
    name: str


def lifecycle_success(
    *,
    message: str = "ok",
    code: str = "ok",
    data: dict[str, Any] | None = None,
    next_action: str = "",
) -> LifecycleResult:
    return LifecycleResult(
        success=True,
        code=code,
        message=message,
        data=data or {},
        next_action=next_action,
    )


def lifecycle_error(
    *,
    code: str,
    message: str,
    next_action: str = "",
    data: dict[str, Any] | None = None,
) -> LifecycleResult:
    return LifecycleResult(
        success=False,
        code=code,
        message=message,
        data=data or {},
        next_action=next_action,
    )


def _build_event(
    *,
    actor: Actor,
    project: str,
    tool_name: str,
    action: str,
    success: bool,
    message: str,
    version: str | None = None,
    preview_key: str | None = None,
    content_sha256: str | None = None,
) -> ToolLifecycleEvent:
    return ToolLifecycleEvent(
        project=project,
        tool_name=tool_name,
        action=action,
        actor_type=actor.type,
        actor_id=actor.id,
        actor_name=actor.name,
        version=version,
        preview_key=preview_key,
        content_sha256=content_sha256,
        success=success,
        message=message,
        created_at=datetime.now(),
    )


def record_lifecycle_event(
    *,
    actor: Actor,
    project: str,
    tool_name: str,
    action: str,
    success: bool,
    message: str,
    version: str | None = None,
    preview_key: str | None = None,
    content_sha256: str | None = None,
) -> None:
    if not db_manager:
        logger.warning("数据库连接不可用，跳过生命周期事件记录")
        return

    event = _build_event(
        actor=actor,
        project=project,
        tool_name=tool_name,
        action=action,
        success=success,
        message=message,
        version=version,
        preview_key=preview_key,
        content_sha256=content_sha256,
    )
    try:
        with db_manager.session_scope() as session:
            session.add(event)
    except Exception:
        logger.exception("生命周期事件记录失败，已跳过")


def _permission_error(scope: str) -> LifecycleResult:
    return lifecycle_error(
        code="permission_denied",
        message=f"缺少权限: {scope}",
        next_action="request_scope",
    )


def _check_scope(actor: Actor, scope: str) -> LifecycleResult | None:
    try:
        require_scope(actor, scope)
        return None
    except PermissionError:
        return _permission_error(scope)


def _tool_filename(name: str) -> str:
    return f"{name}.py"


def _tool_name(filename: str) -> str:
    return filename.removesuffix(".py")


def _database_unavailable_error(message: str = "数据库连接不可用") -> LifecycleResult:
    return lifecycle_error(
        code="database_unavailable",
        message=message,
        next_action="retry_later",
    )


def _find_tool(
    project_name: str, tool_name: str
) -> tuple[ToolIdentity | None, LifecycleResult | None]:
    if not db_manager:
        return None, _database_unavailable_error()

    filename = _tool_filename(tool_name)
    try:
        with db_manager.session_scope() as session:
            statement = select(Tool).where(
                Tool.project == project_name,
                Tool.filename == filename,
            )
            tool = session.exec(statement).first()
            if tool:
                identity = ToolIdentity(
                    id=tool.id,
                    project=tool.project,
                    filename=tool.filename,
                    name=_tool_name(tool.filename),
                )
    except Exception:
        logger.exception("生命周期工具索引查询失败")
        return None, _database_unavailable_error("数据库查询失败")

    if not tool:
        return None, lifecycle_error(
            code="tool_not_found",
            message=f"工具不存在: {project_name}/{tool_name}",
            next_action="check_name",
        )

    return identity, None


def _tool_url(project_name: str, tool_name: str) -> str:
    return f"/user/tools/{project_name}/{tool_name}"


def _publish_uploaded_content(
    actor: Actor,
    project_name: str,
    tool_name: str,
    content: str,
) -> LifecycleResult:
    try:
        validate_tool_entrypoint(content)
    except SyntaxError as exc:
        message = f"Python 语法错误: 第 {exc.lineno} 行 - {exc.msg}"
        record_lifecycle_event(
            actor=actor,
            project=project_name,
            tool_name=tool_name,
            action="tool.publish",
            success=False,
            message=message,
        )
        return lifecycle_error(
            code="invalid_content",
            message=message,
            next_action="fix_syntax",
        )
    except ToolEntryPointError as exc:
        message = str(exc)
        record_lifecycle_event(
            actor=actor,
            project=project_name,
            tool_name=tool_name,
            action="tool.publish",
            success=False,
            message=message,
        )
        return lifecycle_error(
            code="invalid_content",
            message=message,
            next_action="add_main",
        )

    try:
        storage = get_tool_storage()
        result = storage.save_current(
            project_name,
            tool_name,
            content,
            created_by=actor.name or actor.id or "publish",
        )
        if result.get("success"):
            result["url"] = _tool_url(project_name, tool_name)
            local_path = storage.restore_current_to_local(project_name, tool_name)
            if local_path:
                result["local_path"] = local_path
    except Exception as exc:
        logger.exception("上传内容发布失败")
        result = {"success": False, "error": str(exc) or "发布工具失败"}

    success = bool(result.get("success"))
    message = "工具已发布" if success else result.get("error", "发布工具失败")
    if success:
        result["url"] = _tool_url(project_name, tool_name)
    record_lifecycle_event(
        actor=actor,
        project=project_name,
        tool_name=tool_name,
        action="tool.publish",
        success=success,
        message=message,
        version=result.get("version"),
        content_sha256=result.get("content_sha256"),
    )

    if not success:
        return lifecycle_error(
            code="publish_failed",
            message=message,
            next_action="inspect_error",
            data=result,
        )

    return lifecycle_success(message=message, data=result)


def publish_tool(
    actor: Actor,
    project: str,
    name: str,
    content: str,
) -> LifecycleResult:
    scope_error = _check_scope(actor, "tool:publish")
    if scope_error:
        return scope_error

    try:
        project_name, tool_name = validate_tool_identity(project, name)
    except InvalidToolIdentity as exc:
        return lifecycle_error(
            code="invalid_identity", message=str(exc), next_action="check_name"
        )
    return _publish_uploaded_content(actor, project_name, tool_name, content)


def rollback_tool(
    actor: Actor,
    project: str,
    name: str,
    version: str,
) -> LifecycleResult:
    scope_error = _check_scope(actor, "tool:rollback")
    if scope_error:
        return scope_error

    try:
        project_name, tool_name = validate_tool_identity(project, name)
    except InvalidToolIdentity as exc:
        return lifecycle_error(
            code="invalid_identity", message=str(exc), next_action="check_name"
        )
    tool, lookup_error = _find_tool(project_name, tool_name)
    if lookup_error:
        if lookup_error.code == "tool_not_found":
            record_lifecycle_event(
                actor=actor,
                project=project_name,
                tool_name=tool_name,
                action="tool.rollback",
                success=False,
                message=lookup_error.message,
                version=version,
            )
        return lookup_error

    try:
        result = tool_version_service.rollback_tool(tool.id, version)
    except Exception as exc:
        logger.exception("工具回滚失败")
        message = str(exc) or "回滚工具失败"
        data = {"success": False, "error": message, "source_version": version}
        record_lifecycle_event(
            actor=actor,
            project=project_name,
            tool_name=tool_name,
            action="tool.rollback",
            success=False,
            message=message,
            version=version,
        )
        return lifecycle_error(
            code="rollback_failed",
            message=message,
            next_action="inspect_versions",
            data=data,
        )

    success = bool(result.get("success"))
    message = "工具已回滚" if success else result.get("error", "回滚工具失败")
    data = {**result, "source_version": version}
    event_version = result.get("version") or version
    record_lifecycle_event(
        actor=actor,
        project=project_name,
        tool_name=tool_name,
        action="tool.rollback",
        success=success,
        message=message,
        version=event_version,
    )

    if not success:
        return lifecycle_error(
            code="rollback_failed",
            message=message,
            next_action="inspect_versions",
            data=data,
        )

    return lifecycle_success(message=message, data=data)


def preview_tool(
    actor: Actor,
    content: str,
    project: str | None = None,
    name: str | None = None,
) -> LifecycleResult:
    scope_error = _check_scope(actor, "tool:preview")
    if scope_error:
        return scope_error

    result = create_temporary_preview(content)
    success = bool(result.get("success"))
    message = result.get("message") if success else result.get("error", "预览失败")

    if not success:
        return lifecycle_error(
            code=result.get("code") or "preview_failed",
            message=message,
            next_action=result.get("next_action") or "read_preview_log",
            data=result,
        )

    return lifecycle_success(message=message, data=result)


def get_tool_state(actor: Actor, project: str, name: str) -> LifecycleResult:
    scope_error = _check_scope(actor, "tool:read")
    if scope_error:
        return scope_error

    try:
        project_name, tool_name = validate_tool_identity(project, name)
    except InvalidToolIdentity as exc:
        return lifecycle_error(
            code="invalid_identity", message=str(exc), next_action="check_name"
        )
    if not db_manager:
        return _database_unavailable_error()

    filename = _tool_filename(tool_name)
    try:
        with db_manager.session_scope() as session:
            tool_statement = select(Tool).where(
                Tool.project == project_name,
                Tool.filename == filename,
            )
            tool = session.exec(tool_statement).first()
            if not tool:
                return lifecycle_error(
                    code="tool_not_found",
                    message=f"工具不存在: {project_name}/{tool_name}",
                    next_action="check_name",
                )

            version_statement = select(ToolVersion).where(
                ToolVersion.tool_id == tool.id,
            )
            versions_count = len(session.exec(version_statement).all())

            published = bool(tool.current_version or tool.published_at)
            state = {
                "indexed": True,
                "current": bool(tool.current_version),
                "published": published,
                "previewed": False,
                "deleted": False,
            }
            data = {
                "tool": {
                    "id": tool.id,
                    "project": tool.project,
                    "filename": tool.filename,
                    "name": _tool_name(tool.filename),
                    "display_name": tool.display_name,
                    "description": tool.description,
                    "creator": tool.creator,
                    "current_version": tool.current_version,
                    "tags": tool.tags,
                    "created_at": (
                        tool.created_at.isoformat() if tool.created_at else None
                    ),
                    "updated_at": (
                        tool.updated_at.isoformat() if tool.updated_at else None
                    ),
                    "published_at": (
                        tool.published_at.isoformat() if tool.published_at else None
                    ),
                },
                "state": state,
                "versions_count": versions_count,
            }

        return lifecycle_success(message="ok", data=data)
    except Exception:
        logger.exception("生命周期工具状态查询失败")
        return _database_unavailable_error("数据库查询失败")


def _event_limit(limit: int) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = 50
    return max(1, min(value, 200))


def _serialize_event(event: ToolLifecycleEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "project": event.project,
        "tool_name": event.tool_name,
        "action": event.action,
        "actor_type": event.actor_type,
        "actor_id": event.actor_id,
        "actor_name": event.actor_name,
        "version": event.version,
        "preview_key": event.preview_key,
        "content_sha256": event.content_sha256,
        "success": event.success,
        "message": event.message,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def list_tool_events(
    actor: Actor,
    project: str,
    name: str,
    limit: int = 50,
) -> LifecycleResult:
    scope_error = _check_scope(actor, "tool:read")
    if scope_error:
        return scope_error

    try:
        project_name, tool_name = validate_tool_identity(project, name)
    except InvalidToolIdentity as exc:
        return lifecycle_error(
            code="invalid_identity", message=str(exc), next_action="check_name"
        )
    if not db_manager:
        return lifecycle_success(message="ok", data={"events": []})

    try:
        statement = (
            select(ToolLifecycleEvent)
            .where(ToolLifecycleEvent.project == project_name)
            .where(ToolLifecycleEvent.tool_name == tool_name)
            .order_by(ToolLifecycleEvent.created_at.desc())
            .limit(_event_limit(limit))
        )
        with db_manager.session_scope() as session:
            events = session.exec(statement).all()
            rows = [_serialize_event(event) for event in events]
    except Exception:
        logger.exception("生命周期事件列表查询失败")
        return lifecycle_success(message="ok", data={"events": []})

    return lifecycle_success(
        message="ok",
        data={"events": rows},
    )


def delete_tool(actor: Actor, project: str, name: str) -> LifecycleResult:
    scope_error = _check_scope(actor, "tool:delete")
    if scope_error:
        return scope_error

    try:
        project_name, tool_name = validate_tool_identity(project, name)
    except InvalidToolIdentity as exc:
        return lifecycle_error(
            code="invalid_identity", message=str(exc), next_action="check_name"
        )
    result = tool_manage_service.delete_tool(project_name, tool_name)
    success = bool(result.get("success"))
    message = "工具已删除" if success else result.get("error", "删除工具失败")

    if not success:
        record_lifecycle_event(
            actor=actor,
            project=project_name,
            tool_name=tool_name,
            action="tool.delete",
            success=False,
            message=message,
        )
        return lifecycle_error(
            code="delete_failed",
            message=message,
            next_action="inspect_tool",
            data=result,
        )

    if not delete_tool_from_db(project_name, _tool_filename(tool_name)):
        message = "工具 DB 索引删除失败"
        record_lifecycle_event(
            actor=actor,
            project=project_name,
            tool_name=tool_name,
            action="tool.delete",
            success=False,
            message=message,
        )
        return lifecycle_error(
            code="index_delete_failed",
            message=message,
            next_action="retry_delete_index",
            data=result,
        )

    record_lifecycle_event(
        actor=actor,
        project=project_name,
        tool_name=tool_name,
        action="tool.delete",
        success=True,
        message=message,
    )
    return lifecycle_success(message=message, data=result)


def restore_runtime_cache(actor: Actor, project: str, name: str) -> LifecycleResult:
    scope_error = _check_scope(actor, "tool:publish")
    if scope_error:
        return scope_error

    try:
        project_name, tool_name = validate_tool_identity(project, name)
    except InvalidToolIdentity as exc:
        return lifecycle_error(
            code="invalid_identity", message=str(exc), next_action="check_name"
        )
    path = get_tool_storage().restore_current_to_local(project_name, tool_name)
    success = bool(path)
    message = "运行缓存已恢复" if success else "当前工具内容不存在，无法恢复运行缓存"
    record_lifecycle_event(
        actor=actor,
        project=project_name,
        tool_name=tool_name,
        action="tool.restore_runtime_cache",
        success=success,
        message=message,
    )

    if not success:
        return lifecycle_error(
            code="restore_cache_failed",
            message=message,
            next_action="inspect_storage",
        )

    return lifecycle_success(message=message, data={"path": path})
