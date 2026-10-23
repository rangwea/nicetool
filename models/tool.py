"""
Tool 模型
支持 Tool 的 CRUD 操作和版本管理
元数据从文件 header 注释解析，MySQL 作为索引/缓存
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlmodel import Field, SQLModel


class ToolBase(SQLModel):
    """Tool 基础模型"""

    project: str = Field(
        description="所属项目（工具分组名）",
        max_length=100,
        index=True,
    )
    filename: str = Field(
        description="文件名（如 tool_query.py）",
        max_length=200,
    )
    display_name: str = Field(
        default="",
        description="显示标题（从 header 注释解析）",
        max_length=200,
    )
    description: str | None = Field(
        default=None,
        description="工具描述（从 header 注释解析）",
        max_length=1000,
    )
    current_version: str | None = Field(
        default=None,
        description="当前发布版本 tag（如 v3）",
        max_length=50,
    )
    tags: str | None = Field(
        default=None,
        description="工具标签，逗号分隔（如 data,export,finance）",
        max_length=500,
    )


class Tool(ToolBase, table=True):
    """Tool 数据库模型"""

    __tablename__ = "tools"
    __table_args__ = (
        UniqueConstraint("project", "filename", name="uq_tool_project_filename"),
    )

    id: int | None = Field(default=None, primary_key=True, description="Tool ID")
    creator: str | None = Field(
        default=None,
        description="创建者（从 header 注释解析）",
        max_length=100,
    )
    created_at: datetime | None = Field(
        default_factory=datetime.now,
        description="创建时间",
    )
    updated_at: datetime | None = Field(
        default_factory=datetime.now,
        description="更新时间",
    )
    published_at: datetime | None = Field(
        default=None,
        description="最后发布时间",
    )


class ToolCreate(SQLModel):
    """创建 Tool 请求模型"""

    project: str = Field(max_length=100)
    filename: str = Field(max_length=200)
    display_name: str = Field(default="", max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    creator: str | None = Field(default=None, max_length=100)
    tags: str | None = Field(default=None, max_length=500)


class ToolUpdate(SQLModel):
    """更新 Tool 请求模型"""

    filename: str | None = Field(default=None, max_length=200)
    display_name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    current_version: str | None = Field(default=None, max_length=50)
    creator: str | None = Field(default=None, max_length=100)
    tags: str | None = Field(default=None, max_length=500)


class ToolResponse(ToolBase):
    """Tool 响应模型"""

    id: int
    creator: str | None = None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    tags: str | None = None


class ToolVersion(SQLModel, table=True):
    """Tool 已发布版本内容。"""

    __tablename__ = "tool_versions"
    __table_args__ = (UniqueConstraint("tool_id", "version", name="uq_tool_version"),)

    id: int | None = Field(default=None, primary_key=True, description="版本 ID")
    tool_id: int = Field(index=True, description="Tool ID")
    version: str = Field(description="版本号（如 v3）", max_length=50, index=True)
    content: str = Field(sa_column=Column(LONGTEXT), description="工具源码")
    content_sha256: str = Field(description="源码 SHA256", max_length=64, index=True)
    content_size: int = Field(default=0, description="源码字节数")
    status: str = Field(
        default="published",
        description="状态：published/deleted",
        max_length=30,
        index=True,
    )
    created_by: str = Field(default="system", description="创建人", max_length=100)
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    published_at: datetime = Field(default_factory=datetime.now, description="发布时间")
    deleted_at: datetime | None = Field(default=None, description="删除时间")


class ToolLifecycleEvent(SQLModel, table=True):
    """Tool 生命周期事件索引。"""

    __tablename__ = "tool_lifecycle_events"
    __table_args__ = (
        Index("idx_tle_tool", "project", "tool_name"),
        Index("idx_tle_action", "action"),
        Index("idx_tle_actor", "actor_type", "actor_id"),
        Index("idx_tle_version", "version"),
        Index("idx_tle_preview_key", "preview_key"),
        Index("idx_tle_created_at", "created_at"),
    )

    id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            primary_key=True,
            autoincrement=True,
            comment="事件 ID",
        ),
    )
    project: str = Field(max_length=100, description="所属项目")
    tool_name: str = Field(max_length=200, description="工具名")
    action: str = Field(max_length=100, description="生命周期动作")
    actor_type: str = Field(max_length=50, description="user/token/system")
    actor_id: str = Field(
        default="",
        sa_column=Column(
            String(100),
            nullable=False,
            server_default=text("''"),
            comment="操作者 ID",
        ),
    )
    actor_name: str = Field(
        default="",
        sa_column=Column(
            String(255),
            nullable=False,
            server_default=text("''"),
            comment="操作者展示名",
        ),
    )
    version: str | None = Field(default=None, max_length=50)
    preview_key: str | None = Field(default=None, max_length=128)
    content_sha256: str | None = Field(default=None, max_length=64)
    success: bool = Field(
        default=True,
        sa_column=Column(
            Boolean,
            nullable=False,
            server_default=text("TRUE"),
            comment="是否成功",
        ),
    )
    message: str | None = Field(default=None, max_length=1000)
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(
            DateTime,
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            comment="创建时间",
        ),
    )
