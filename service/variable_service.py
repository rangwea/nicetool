"""全局工具变量业务服务。"""

from datetime import UTC, datetime

from sqlmodel import select

from core.database import db_manager
from core.logger import get_logger
from models.variable import (
    Variable,
    VariableCreate,
    VariableResponse,
    VariableUpdate,
)

logger = get_logger(__name__)


def _normalize_key(key: str) -> str:
    normalized = key.strip()
    if not normalized:
        raise ValueError("变量 Key 不能为空")
    return normalized


def create_variable(data: VariableCreate) -> VariableResponse:
    """创建变量。"""
    key = _normalize_key(data.key)
    with db_manager.session_scope() as session:
        existing = session.exec(select(Variable).where(Variable.key == key)).first()
        if existing:
            raise ValueError(f"变量 Key '{key}' 已存在")

        record = Variable(key=key, value=data.value, remark=data.remark.strip())
        session.add(record)
        session.commit()
        session.refresh(record)
        logger.info(f"变量 '{key}' 创建成功")
        return VariableResponse(**record.model_dump())


def list_variables(search: str | None = None) -> list[VariableResponse]:
    """列出变量，支持按 Key 或备注搜索。"""
    with db_manager.session_scope() as session:
        statement = select(Variable)
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                (Variable.key.like(pattern)) | (Variable.remark.like(pattern))
            )
        statement = statement.order_by(Variable.key.asc())
        records = session.exec(statement).all()
        return [VariableResponse(**record.model_dump()) for record in records]


def list_variable_keys(search: str | None = None) -> list[dict[str, str]]:
    """列出可供 CLI 发现的 Key 和备注，不读取变量值。"""
    with db_manager.session_scope() as session:
        statement = select(Variable.key, Variable.remark)
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                (Variable.key.like(pattern)) | (Variable.remark.like(pattern))
            )
        statement = statement.order_by(Variable.key.asc())
        return [
            {"key": key, "remark": remark or ""}
            for key, remark in session.exec(statement).all()
        ]


def get_variable(variable_id: int) -> VariableResponse | None:
    """按 ID 获取变量。"""
    with db_manager.session_scope() as session:
        record = session.get(Variable, variable_id)
        return VariableResponse(**record.model_dump()) if record else None


def get_variable_value(key: str) -> str | None:
    """按 Key 获取变量值，供工具运行时读取。"""
    normalized = _normalize_key(key)
    with db_manager.session_scope() as session:
        record = session.exec(
            select(Variable).where(Variable.key == normalized)
        ).first()
        return record.value if record else None


def update_variable(
    variable_id: int,
    data: VariableUpdate,
) -> VariableResponse | None:
    """更新变量。"""
    with db_manager.session_scope() as session:
        record = session.get(Variable, variable_id)
        if not record:
            return None

        if data.key is not None:
            key = _normalize_key(data.key)
            if key != record.key:
                existing = session.exec(
                    select(Variable).where(Variable.key == key)
                ).first()
                if existing:
                    raise ValueError(f"变量 Key '{key}' 已存在")
                record.key = key
        if data.value is not None:
            record.value = data.value
        if data.remark is not None:
            record.remark = data.remark.strip()

        record.updated_at = datetime.now(UTC).replace(tzinfo=None)
        session.add(record)
        session.commit()
        session.refresh(record)
        logger.info(f"变量 '{record.key}' 更新成功")
        return VariableResponse(**record.model_dump())


def delete_variable(variable_id: int) -> bool:
    """删除变量。"""
    with db_manager.session_scope() as session:
        record = session.get(Variable, variable_id)
        if not record:
            return False
        key = record.key
        session.delete(record)
        session.commit()
        logger.info(f"变量 '{key}' 已删除")
        return True
