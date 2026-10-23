"""
应用配置管理模块
使用 Pydantic Settings 进行配置管理和验证
"""

import os
from dataclasses import dataclass

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_TYPE_ALIASES = {
    "dev": "dev",
    "uat": "uat",
    "prod": "prod",
}


@dataclass(frozen=True)
class EnvConfigSelection:
    """启动时选中的 dotenv 配置，不包含任何配置值。"""

    env_type: str
    source: str
    env_files: tuple[str, ...]


def _resolve_env_config(
    env_file: str | None = None,
    env_type: str | None = None,
) -> EnvConfigSelection:
    """按 ENV_FILE > ENV_TYPE 的优先级解析 dotenv 文件。"""
    explicit_env_file = (
        os.getenv("ENV_FILE", "") if env_file is None else env_file
    ).strip()
    raw_env_type = (
        (os.getenv("ENV_TYPE", "prod") if env_type is None else env_type)
        .strip()
        .lower()
    )

    if explicit_env_file:
        env_files = tuple(
            item.strip() for item in explicit_env_file.split(",") if item.strip()
        )
        if not env_files:
            raise RuntimeError("ENV_FILE 未包含有效的配置文件路径")
        normalized_type = _ENV_TYPE_ALIASES.get(raw_env_type, raw_env_type or "custom")
        return EnvConfigSelection(normalized_type, "ENV_FILE", env_files)

    try:
        normalized_type = _ENV_TYPE_ALIASES[raw_env_type]
    except KeyError as error:
        supported = ", ".join(sorted(_ENV_TYPE_ALIASES))
        raise RuntimeError(
            f"不支持的 ENV_TYPE={raw_env_type!r}，可选值：{supported}"
        ) from error

    return EnvConfigSelection(
        normalized_type,
        "ENV_TYPE",
        (".env", f".env.{normalized_type}"),
    )


_ENV_CONFIG = _resolve_env_config()


class Settings(BaseSettings):
    """应用配置类"""

    # 工具目录配置
    tools_dir: str = Field(default="./tools", description="工具目录路径")

    # 服务器配置
    host: str = Field(default="0.0.0.0", description="服务器绑定地址")
    port: int = Field(default=8000, ge=1, le=65535, description="服务器端口")
    debug: bool = Field(default=False, description="调试模式")

    # NiceGUI配置
    storage_secret: str = Field(
        default="nicetool-secret-change-in-production",
        description="NiceGUI存储密钥",
    )
    language: str = Field(default="zh-CN", description="平台界面语言")
    project_path: str = Field(default="", description="项目路径前缀，如 /nicetool")

    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")

    # 数据库配置
    mysql_host: str = Field(default="localhost", description="MySQL主机地址")
    mysql_port: int = Field(default=3306, ge=1, le=65535, description="MySQL端口")
    mysql_user: str = Field(default="root", description="MySQL用户名")
    mysql_password: str = Field(default="", description="MySQL密码")
    mysql_database: str = Field(default="nicetool", description="MySQL数据库名")
    mysql_charset: str = Field(default="utf8mb4", description="MySQL字符集")

    # 连接池配置
    mysql_pool_size: int = Field(default=10, ge=1, description="MySQL连接池大小")
    mysql_max_overflow: int = Field(default=20, ge=0, description="MySQL连接池最大溢出")
    mysql_pool_timeout: int = Field(default=30, ge=1, description="MySQL连接池超时时间")
    mysql_pool_recycle: int = Field(default=3600, ge=1, description="MySQL连接回收时间")

    request_timeout: int = Field(default=30, ge=1, description="请求超时时间（秒）")

    # OAuth2/OIDC 认证配置
    auth_enabled: bool = Field(default=False, description="是否启用登录鉴权")
    auth_provider_name: str = Field(
        default="enterprise-sso", description="认证提供方名称"
    )
    auth_provider_profile: str = Field(
        default="oidc", description="Provider profile: oidc/oauth2/enterprise_oa"
    )
    auth_enterprise_oa_base_url: str = Field(
        default="", description="企业 OA OAuth2 根地址"
    )
    auth_issuer: str = Field(default="", description="OIDC issuer")
    auth_authorization_endpoint: str = Field(default="", description="OAuth2 授权端点")
    auth_token_endpoint: str = Field(default="", description="OAuth2 token 端点")
    auth_userinfo_endpoint: str = Field(default="", description="OIDC userinfo 端点")
    auth_jwks_uri: str = Field(default="", description="OIDC JWKS URI")
    auth_client_id: str = Field(default="", description="OAuth2 client_id")
    auth_client_secret: str = Field(default="", description="OAuth2 client_secret")
    auth_redirect_uri: str = Field(default="", description="OAuth2 callback URL")
    auth_scopes: str = Field(
        default="openid profile email", description="OAuth2 scopes"
    )
    auth_email_verified_claim: str = Field(
        default="email_verified", description="可信邮箱验证 claim；留空表示不可信"
    )
    auth_email_verified_value: str = Field(
        default="true", description="通用 OAuth2 邮箱验证 claim 的可信值"
    )
    auth_token_include_redirect_uri: bool = Field(
        default=True,
        description="authorization_code 换 token 时是否提交 redirect_uri",
    )
    auth_cookie_name: str = Field(
        default="nicetool_session", description="登录 cookie 名"
    )
    auth_flow_cookie_name: str = Field(
        default="nicetool_auth_flow", description="OAuth state/nonce 临时会话 cookie"
    )
    auth_require_https_cookie: bool = Field(
        default=False, description="Cookie 是否仅 HTTPS"
    )
    auth_user_id_claim: str = Field(default="sub", description="用户唯一 ID claim")
    auth_username_claim: str = Field(
        default="preferred_username", description="用户名 claim"
    )
    auth_email_claim: str = Field(default="email", description="邮箱 claim")
    auth_display_name_claim: str = Field(default="name", description="显示名 claim")
    auth_avatar_claim: str = Field(default="picture", description="头像 claim")
    auth_groups_claim: str = Field(default="groups", description="用户组 claim")
    auth_groups_separator: str = Field(default=",", description="字符串用户组分隔符")
    auth_admin_groups: str = Field(default="", description="管理员用户组，逗号分隔")
    auth_admin_users: str = Field(default="", description="管理员用户名/邮箱，逗号分隔")
    auth_protected_paths: str = Field(
        default="/user,/admin,/api", description="需要登录路径前缀"
    )
    auth_admin_paths: str = Field(default="/admin", description="需要管理员路径前缀")
    auth_public_paths: str = Field(
        default="/,/health,/docs,/redoc,/openapi.json,/auth,/api/auth/device/start,/api/auth/device/token,/client/tool,/api/downloads,/api/init.sh,/api/install.sh",
        description="免登录路径前缀",
    )
    auth_enable_personal_tokens: bool = Field(
        default=True,
        description="是否允许 Bearer 个人访问令牌",
    )
    auth_jwt_secret: str = Field(default="", description="网页 JWT HMAC 密钥")
    auth_jwt_algorithm: str = Field(default="HS256", description="网页 JWT 算法")
    auth_jwt_issuer: str = Field(default="nicetool", description="网页 JWT issuer")
    auth_jwt_audience: str = Field(
        default="nicetool-web", description="网页 JWT audience"
    )
    auth_jwt_expires_minutes: int = Field(
        default=30, ge=1, description="网页 JWT 有效期（分钟）"
    )

    model_config = SettingsConfigDict(
        env_file=_ENV_CONFIG.env_files,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # 忽略额外的环境变量
    )

    def get_tools_dir(self) -> str:
        """获取工具目录路径"""
        return self.tools_dir

    def get_env_config_selection(self) -> EnvConfigSelection:
        """返回可安全写入日志的环境配置选择信息。"""
        return _ENV_CONFIG

    def get_project_path(self) -> str:
        """获取规范化后的项目路径前缀。"""
        raw_path = (self.project_path or "").strip()
        if not raw_path or raw_path == "/":
            return ""
        return "/" + raw_path.strip("/")

    def path_for(self, path: str = "") -> str:
        """为站内路径添加项目路径前缀。"""
        project_path = self.get_project_path()
        if not path:
            return project_path or "/"
        normalized_path = "/" + path.strip("/")
        return f"{project_path}{normalized_path}" if project_path else normalized_path

    def get_nicegui_config(self) -> dict:
        """获取NiceGUI配置"""
        return {
            "storage_secret": self.storage_secret,
            "language": self.language,
            "mount_path": self.get_project_path(),
        }

    def csv_list(self, value: str) -> list[str]:
        """解析逗号分隔配置。"""
        return [item.strip() for item in value.split(",") if item.strip()]

    def get_mysql_url(self) -> str:
        """获取MySQL连接URL"""
        return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset={self.mysql_charset}"

    def get_mysql_config(self) -> dict:
        """获取MySQL配置"""
        return {
            "url": self.get_mysql_url(),
            "pool_size": self.mysql_pool_size,
            "max_overflow": self.mysql_max_overflow,
            "pool_timeout": self.mysql_pool_timeout,
            "pool_recycle": self.mysql_pool_recycle,
        }


# 创建全局设置实例
settings = Settings()

# 导出常用配置
__all__ = ["EnvConfigSelection", "Settings", "settings"]
