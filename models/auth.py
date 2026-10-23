"""
认证与用户模型

支持本地密码账号、外部 OAuth2/OIDC 身份映射和个人访问令牌。
"""

import secrets
from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class AuthUser(SQLModel, table=True):
    """统一的本地用户主体。"""

    __tablename__ = "auth_users"

    id: int | None = Field(default=None, primary_key=True, description="用户 ID")
    provider: str = Field(default="local", max_length=100, description="认证提供方")
    subject: str = Field(max_length=255, index=True, description="外部用户唯一 ID")
    username: str = Field(max_length=100, index=True, description="用户名")
    email: str | None = Field(default=None, max_length=255, index=True)
    email_verified: bool = Field(default=False, description="邮箱是否已可信验证")
    display_name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=1000)
    groups: str | None = Field(
        default=None, max_length=2000, description="逗号分隔用户组"
    )
    role: str = Field(
        default="user", max_length=50, index=True, description="user/admin"
    )
    is_active: bool = Field(default=True, description="是否启用")
    password_hash: str | None = Field(
        default=None, max_length=512, description="Argon2id 密码哈希"
    )
    must_change_password: bool = Field(
        default=False, description="下次登录后必须修改密码"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_login_at: datetime | None = Field(default=None)


class AuthIdentity(SQLModel, table=True):
    """外部认证身份到本地用户的稳定映射。"""

    __tablename__ = "auth_identities"
    __table_args__ = (
        UniqueConstraint(
            "provider", "subject", name="uq_auth_identity_provider_subject"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, description="本地用户 ID")
    provider: str = Field(max_length=100, index=True)
    subject: str = Field(max_length=255, index=True)
    email: str | None = Field(default=None, max_length=255, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class AuthToken(SQLModel, table=True):
    """CLI/AI agent 使用的个人访问令牌"""

    __tablename__ = "auth_tokens"

    id: int | None = Field(default=None, primary_key=True, description="Token ID")
    user_id: int = Field(index=True, description="所属用户 ID")
    name: str = Field(default="default", max_length=100, description="Token 名称")
    token_hash: str = Field(max_length=128, index=True, description="Token 哈希")
    token_prefix: str = Field(max_length=16, index=True, description="Token 前缀")
    is_active: bool = Field(default=True, description="是否启用")
    created_at: datetime = Field(default_factory=datetime.now)
    last_used_at: datetime | None = Field(default=None)
    expires_at: datetime | None = Field(default=None)


class AuthDeviceAuthorization(SQLModel, table=True):
    """安装脚本使用的一次性浏览器授权。"""

    __tablename__ = "auth_device_authorizations"

    id: int | None = Field(default=None, primary_key=True)
    device_code_hash: str = Field(max_length=128, unique=True, index=True)
    user_code: str = Field(max_length=16, unique=True, index=True)
    token_env: str = Field(max_length=100)
    status: str = Field(default="pending", max_length=20, index=True)
    user_id: int | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime = Field(index=True)


class AuthUserResource(SQLModel, table=True):
    """用户与资源授权关系。"""

    __tablename__ = "auth_user_resources"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "resource_type", "resource_name", name="uq_auth_user_resource"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    resource_type: str = Field(max_length=50, index=True)
    resource_name: str = Field(max_length=200, index=True)


def generate_auth_token() -> str:
    """生成个人访问令牌明文，只在创建时返回一次。"""
    return f"nt_{secrets.token_urlsafe(32)}"
