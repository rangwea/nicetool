"""用户项目访问授权服务。"""

from sqlalchemy import delete
from sqlmodel import select

from core.auth.service import auth_service
from core.database import db_manager
from models.auth import AuthUser, AuthUserResource

PROJECT_RESOURCE = "project"


def allowed_projects(user: AuthUser | object | None) -> set[str] | None:
    """返回允许访问的项目；None 表示不限制。"""
    if not auth_service.is_enabled() or getattr(user, "role", None) == "admin":
        return None
    user_id = getattr(user, "id", None)
    if not user_id or not db_manager:
        return set()
    with db_manager.session_scope() as session:
        statement = (
            select(AuthUserResource.resource_name)
            .where(AuthUserResource.user_id == user_id)
            .where(AuthUserResource.resource_type == PROJECT_RESOURCE)
            .distinct()
        )
        return set(session.exec(statement).all())


def can_access_project(user: AuthUser | object | None, project: str) -> bool:
    projects = allowed_projects(user)
    return projects is None or project in projects


def filter_tools_for_user(
    tools: list[dict], user: AuthUser | object | None
) -> list[dict]:
    projects = allowed_projects(user)
    if projects is None:
        return tools
    return [tool for tool in tools if tool.get("project") in projects]


def get_user_projects(user_id: int) -> list[str]:
    if not db_manager:
        return []
    with db_manager.session_scope() as session:
        return list(
            session.exec(
                select(AuthUserResource.resource_name)
                .where(AuthUserResource.user_id == user_id)
                .where(AuthUserResource.resource_type == PROJECT_RESOURCE)
                .order_by(AuthUserResource.resource_name)
            ).all()
        )


def update_user_projects(user_id: int, projects: list[str]) -> None:
    """整体替换普通用户的项目授权。"""
    if not db_manager:
        raise RuntimeError("数据库连接不可用")
    clean_projects = sorted(
        {project.strip() for project in projects if project.strip()}
    )
    with db_manager.session_scope() as session:
        user = session.get(AuthUser, user_id)
        if not user:
            raise ValueError("用户不存在")
        if user.role == "admin":
            raise ValueError("管理员自动拥有全部项目权限，无需配置")
        session.exec(
            delete(AuthUserResource)
            .where(AuthUserResource.user_id == user_id)
            .where(AuthUserResource.resource_type == PROJECT_RESOURCE)
        )
        for project in clean_projects:
            session.add(
                AuthUserResource(
                    user_id=user_id,
                    resource_type=PROJECT_RESOURCE,
                    resource_name=project,
                )
            )
