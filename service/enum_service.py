"""
枚举定义服务层
"""

from datetime import datetime

from sqlmodel import select

from core.database import db_manager
from core.logger import get_logger
from models.enum_definition import (
    EnumDefinition,
    EnumDefinitionCreate,
    EnumDefinitionResponse,
    EnumDefinitionUpdate,
    normalize_enum_value,
)

logger = get_logger(__name__)


def _normalize_values(values: list[dict]) -> list[dict[str, str]]:
    normalized = [normalize_enum_value(item) for item in values]
    keys = [item["key"] for item in normalized if item["key"]]
    if len(keys) != len(set(keys)):
        raise ValueError("枚举 key 不能重复")
    if any(not item["key"] for item in normalized):
        raise ValueError("枚举 key 不能为空")
    return normalized


def create_enum_definition(data: EnumDefinitionCreate) -> EnumDefinitionResponse:
    """创建枚举定义"""
    with db_manager.session_scope() as session:
        existing = session.exec(
            select(EnumDefinition).where(EnumDefinition.name == data.name)
        ).first()
        if existing:
            raise ValueError(f"枚举名称 '{data.name}' 已存在")

        values = _normalize_values(data.values or [])
        record = EnumDefinition(
            name=data.name.strip(),
            description=(data.description or "").strip(),
            values=values,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        logger.info(f"枚举 '{record.name}' 创建成功")
        return EnumDefinitionResponse(**record.model_dump())


def get_enum_definition(enum_id: int) -> EnumDefinitionResponse | None:
    """获取枚举详情"""
    with db_manager.session_scope() as session:
        record = session.get(EnumDefinition, enum_id)
        if record:
            return EnumDefinitionResponse(**record.model_dump())
        return None


def get_enum_definition_by_name(name: str) -> EnumDefinitionResponse | None:
    """按枚举名称获取配置（供工具等调用方使用）"""
    with db_manager.session_scope() as session:
        record = session.exec(
            select(EnumDefinition).where(EnumDefinition.name == name)
        ).first()
        if record:
            return EnumDefinitionResponse(**record.model_dump())
        return None


def list_enum_definitions(
    skip: int = 0,
    limit: int = 500,
    search: str | None = None,
) -> list[EnumDefinitionResponse]:
    """枚举列表"""
    with db_manager.session_scope() as session:
        statement = select(EnumDefinition)
        if search:
            pattern = f"%{search}%"
            statement = statement.where(
                (EnumDefinition.name.like(pattern))
                | (EnumDefinition.description.like(pattern))
            )
        statement = (
            statement.offset(skip)
            .limit(limit)
            .order_by(EnumDefinition.updated_at.desc())
        )
        records = session.exec(statement).all()
        return [EnumDefinitionResponse(**item.model_dump()) for item in records]


def update_enum_definition(
    enum_id: int, data: EnumDefinitionUpdate
) -> EnumDefinitionResponse | None:
    """更新枚举定义"""
    with db_manager.session_scope() as session:
        record = session.get(EnumDefinition, enum_id)
        if not record:
            return None

        if data.name is not None:
            name = data.name.strip()
            if name != record.name:
                existing = session.exec(
                    select(EnumDefinition).where(EnumDefinition.name == name)
                ).first()
                if existing:
                    raise ValueError(f"枚举名称 '{name}' 已存在")
            record.name = name

        if data.description is not None:
            record.description = data.description.strip()

        if data.values is not None:
            record.values = _normalize_values(data.values)

        record.updated_at = datetime.now()
        session.add(record)
        session.commit()
        session.refresh(record)
        logger.info(f"枚举 '{record.name}' 更新成功")
        return EnumDefinitionResponse(**record.model_dump())


def delete_enum_definition(enum_id: int) -> bool:
    """删除枚举定义"""
    with db_manager.session_scope() as session:
        record = session.get(EnumDefinition, enum_id)
        if not record:
            return False
        session.delete(record)
        session.commit()
        logger.info(f"枚举 id={enum_id} 已删除")
        return True
