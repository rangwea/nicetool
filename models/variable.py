"""全局工具变量模型。"""

from datetime import datetime

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class VariableBase(SQLModel):
    """变量公共字段。"""

    key: str = Field(max_length=191, index=True, unique=True)
    value: str = Field(sa_column=Column(Text, nullable=False))
    remark: str = Field(default="", sa_column=Column(Text, nullable=False))


class Variable(VariableBase, table=True):
    """供工具读取的全局变量。"""

    __tablename__ = "variables"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class VariableCreate(VariableBase):
    """创建变量请求。"""


class VariableUpdate(SQLModel):
    """更新变量请求。"""

    key: str | None = Field(default=None, max_length=191)
    value: str | None = None
    remark: str | None = None


class VariableResponse(VariableBase):
    """变量响应。"""

    id: int
    created_at: datetime
    updated_at: datetime
