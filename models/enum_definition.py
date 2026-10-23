"""
枚举定义模型
存储可复用的 key-value-备注 枚举配置
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class EnumDefinitionBase(SQLModel):
    """枚举定义基础字段"""

    name: str = Field(
        description="枚举名称",
        max_length=100,
        index=True,
        unique=True,
    )
    description: str | None = Field(
        default="",
        description="枚举描述",
        max_length=500,
    )
    values: list[dict[str, str]] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="枚举值列表，每项含 key、value、remark",
    )


class EnumDefinition(EnumDefinitionBase, table=True):
    """枚举定义数据库模型"""

    __tablename__ = "enum_definitions"

    id: int | None = Field(default=None, primary_key=True, description="枚举ID")
    created_at: datetime | None = Field(
        default_factory=datetime.now,
        description="创建时间",
    )
    updated_at: datetime | None = Field(
        default_factory=datetime.now,
        description="更新时间",
    )


class EnumDefinitionCreate(SQLModel):
    """创建枚举请求"""

    name: str = Field(max_length=100)
    description: str | None = Field(default="", max_length=500)
    values: list[dict[str, str]] = Field(default_factory=list)


class EnumDefinitionUpdate(SQLModel):
    """更新枚举请求"""

    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    values: list[dict[str, str]] | None = None


class EnumDefinitionResponse(EnumDefinitionBase):
    """枚举响应"""

    id: int
    created_at: datetime
    updated_at: datetime


def normalize_enum_value(item: dict[str, Any]) -> dict[str, str]:
    """将任意条目规范为 key / value / remark"""
    key = str(item.get("key", item.get("name", ""))).strip()
    value = str(item.get("value", key)).strip()
    remark = str(
        item.get("remark", item.get("desc", item.get("description", "")))
    ).strip()
    return {"key": key, "value": value, "remark": remark}
