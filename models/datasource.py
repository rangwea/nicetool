"""
数据源配置模型
支持MySQL和MongoDB数据源的配置管理
"""

from datetime import datetime

from sqlmodel import Column, Field, SQLModel, String


class DataSourceBase(SQLModel):
    """数据源基础模型"""

    name: str = Field(
        description="数据源名称",
        max_length=100,
        index=True,
        unique=True,
    )
    type: str = Field(
        description="数据源类型: mysql或mongodb",
        sa_column=Column(String(20)),
    )
    host: str = Field(
        description="主机地址",
        max_length=255,
    )
    port: int = Field(
        description="端口号",
        ge=1,
        le=65535,
    )
    username: str = Field(
        description="用户名",
        max_length=100,
    )
    password: str = Field(
        description="密码",
        max_length=255,
    )
    database: str = Field(
        description="数据库名称",
        max_length=100,
    )
    description: str | None = Field(
        default=None,
        description="描述信息",
        max_length=500,
    )
    is_active: bool = Field(
        default=True,
        description="是否启用",
    )

    # MySQL特有配置
    charset: str | None = Field(
        default="utf8mb4",
        description="MySQL字符集",
        max_length=50,
    )
    pool_size: int | None = Field(
        default=10,
        description="连接池大小",
        ge=1,
        le=100,
    )
    max_overflow: int | None = Field(
        default=20,
        description="连接池最大溢出",
        ge=0,
        le=100,
    )
    pool_timeout: int | None = Field(
        default=30,
        description="连接池超时时间(秒)",
        ge=1,
    )
    pool_recycle: int | None = Field(
        default=3600,
        description="连接回收时间(秒)",
        ge=60,
    )

    # MongoDB特有配置
    auth_source: str | None = Field(
        default="admin",
        description="MongoDB认证数据库",
        max_length=100,
    )
    replica_set: str | None = Field(
        default=None,
        description="MongoDB副本集名称",
        max_length=100,
    )
    min_pool_size: int | None = Field(
        default=0,
        description="MongoDB最小连接池大小",
        ge=0,
        le=100,
    )
    max_pool_size: int | None = Field(
        default=100,
        description="MongoDB最大连接池大小",
        ge=1,
        le=1000,
    )
    timezone: str | None = Field(
        default=None,
        description="MongoDB BSON 时间解码时区",
        max_length=64,
    )


class DataSource(DataSourceBase, table=True):
    """数据源表模型"""

    __tablename__ = "datasources"

    id: int | None = Field(
        default=None,
        primary_key=True,
        description="主键ID",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="创建时间",
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="更新时间",
    )


class DataSourceCreate(DataSourceBase):
    """创建数据源请求模型"""


class DataSourceUpdate(SQLModel):
    """更新数据源请求模型"""

    name: str | None = Field(default=None, max_length=100)
    type: str | None = None
    host: str | None = Field(default=None, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = Field(default=None, max_length=100)
    password: str | None = Field(default=None, max_length=255)
    database: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None

    charset: str | None = Field(default=None, max_length=50)
    pool_size: int | None = Field(default=None, ge=1, le=100)
    max_overflow: int | None = Field(default=None, ge=0, le=100)
    pool_timeout: int | None = Field(default=None, ge=1)
    pool_recycle: int | None = Field(default=None, ge=60)

    auth_source: str | None = Field(default=None, max_length=100)
    replica_set: str | None = Field(default=None, max_length=100)
    min_pool_size: int | None = Field(default=None, ge=0, le=100)
    max_pool_size: int | None = Field(default=None, ge=1, le=1000)
    timezone: str | None = Field(default=None, max_length=64)


class DataSourceResponse(DataSourceBase):
    """数据源响应模型"""

    id: int
    created_at: datetime
    updated_at: datetime
