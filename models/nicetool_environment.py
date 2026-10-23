"""NiceTool 客户端环境配置模型。"""

from datetime import datetime

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class NiceToolEnvironmentBase(SQLModel):
    """NiceTool 环境公共字段。"""

    name: str = Field(max_length=64, index=True, unique=True)
    url: str = Field(max_length=500)
    token_env: str = Field(max_length=128)
    production: bool = False
    is_default: bool = False
    enabled: bool = True
    sort_order: int = 0
    remark: str = Field(default="", sa_column=Column(Text, nullable=False))


class NiceToolEnvironment(NiceToolEnvironmentBase, table=True):
    """由 ``/init.sh`` 下发给 NiceTool 客户端的环境。"""

    __tablename__ = "nicetool_environments"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class NiceToolEnvironmentCreate(NiceToolEnvironmentBase):
    """创建 NiceTool 环境请求。"""


class NiceToolEnvironmentUpdate(SQLModel):
    """更新 NiceTool 环境请求。"""

    name: str | None = Field(default=None, max_length=64)
    url: str | None = Field(default=None, max_length=500)
    token_env: str | None = Field(default=None, max_length=128)
    production: bool | None = None
    is_default: bool | None = None
    enabled: bool | None = None
    sort_order: int | None = None
    remark: str | None = None


class NiceToolEnvironmentResponse(NiceToolEnvironmentBase):
    """NiceTool 环境响应。"""

    id: int
    created_at: datetime
    updated_at: datetime
