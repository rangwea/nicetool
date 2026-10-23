"""Authentication module for local, OIDC/OAuth2, web JWT, and CLI tokens."""

import hashlib
import re
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlmodel import select

from core.auth.actor import ALL_TOOL_SCOPES
from core.database import db_manager
from core.logger import get_logger
from core.settings import settings
from models.auth import (
    AuthDeviceAuthorization,
    AuthIdentity,
    AuthToken,
    AuthUser,
    generate_auth_token,
)

logger = get_logger(__name__)


class AuthService:
    """Deep authentication module exposed to routes, middleware, and UI."""

    SESSION_STATE = "oauth_state"
    SESSION_NONCE = "oauth_nonce"
    SESSION_RETURN_TO = "auth_return_to"

    def __init__(self) -> None:
        self._metadata_cache: dict[str, Any] | None = None
        self._jwks_cache: dict[str, Any] | None = None
        self._password_hasher = PasswordHasher()
        self._login_failures: dict[str, list[float]] = {}

    def is_enabled(self) -> bool:
        return settings.auth_enabled

    def public_path_prefixes(self) -> list[str]:
        return settings.csv_list(settings.auth_public_paths)

    def protected_path_prefixes(self) -> list[str]:
        return settings.csv_list(settings.auth_protected_paths)

    def admin_path_prefixes(self) -> list[str]:
        return settings.csv_list(settings.auth_admin_paths)

    def provider_profile(self) -> str:
        return settings.auth_provider_profile.strip().lower()

    def external_login_enabled(self) -> bool:
        return bool(settings.auth_client_id and settings.auth_client_secret)

    def enterprise_oa_base_url(self) -> str:
        base_url = settings.auth_enterprise_oa_base_url or settings.auth_issuer
        if not base_url:
            raise ValueError("auth_enterprise_oa_base_url 或 auth_issuer 未配置")
        return base_url.rstrip("/")

    def enterprise_oa_metadata(self) -> dict[str, Any]:
        base_url = self.enterprise_oa_base_url()
        return {
            "issuer": settings.auth_issuer or base_url,
            "authorization_endpoint": f"{base_url}/oauth2/authorize",
            "token_endpoint": f"{base_url}/oauth2/token",
            "userinfo_endpoint": f"{base_url}/oauth2/userinfo",
            "jwks_uri": f"{base_url}/.well-known/jwks.json",
        }

    async def get_provider_metadata(self) -> dict[str, Any]:
        """Return explicit OAuth metadata or discover an OIDC provider."""
        profile = self.provider_profile()
        if profile == "enterprise_oa":
            return self.enterprise_oa_metadata()

        explicit = {
            "issuer": settings.auth_issuer,
            "authorization_endpoint": settings.auth_authorization_endpoint,
            "token_endpoint": settings.auth_token_endpoint,
            "userinfo_endpoint": settings.auth_userinfo_endpoint,
            "jwks_uri": settings.auth_jwks_uri,
        }
        if profile == "oauth2":
            required = ("authorization_endpoint", "token_endpoint", "userinfo_endpoint")
            if not all(explicit[key] for key in required):
                raise ValueError(
                    "OAuth2 provider 必须配置 authorization/token/userinfo 端点"
                )
            return explicit

        if self._metadata_cache:
            return self._metadata_cache
        if not settings.auth_issuer:
            raise ValueError("OIDC provider 必须配置 auth_issuer")

        discovery_url = (
            settings.auth_issuer.rstrip("/") + "/.well-known/openid-configuration"
        )
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            response = await client.get(discovery_url)
            response.raise_for_status()
            discovered = response.json()
        self._metadata_cache = {
            **discovered,
            **{k: v for k, v in explicit.items() if v},
        }
        return self._metadata_cache

    async def build_authorization_url(
        self, request_url: str, return_to: str
    ) -> tuple[str, str, str | None]:
        metadata = await self.get_provider_metadata()
        state = secrets.token_urlsafe(24)
        nonce = secrets.token_urlsafe(24) if self.provider_profile() == "oidc" else None
        query = {
            "response_type": "code",
            "client_id": settings.auth_client_id,
            "redirect_uri": settings.auth_redirect_uri or request_url,
            "scope": settings.auth_scopes,
            "state": state,
        }
        if nonce:
            query["nonce"] = nonce
        return f"{metadata['authorization_endpoint']}?{urlencode(query)}", state, nonce

    async def exchange_code(self, code: str, callback_url: str) -> dict[str, Any]:
        metadata = await self.get_provider_metadata()
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.auth_client_id,
            "client_secret": settings.auth_client_secret,
        }
        if settings.auth_token_include_redirect_uri and self.provider_profile() not in {
            "enterprise_oa",
        }:
            data["redirect_uri"] = settings.auth_redirect_uri or callback_url
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            response = await client.post(metadata["token_endpoint"], data=data)
            response.raise_for_status()
            return response.json()

    async def validate_id_token(
        self, id_token: str | None, expected_nonce: str | None
    ) -> dict[str, Any]:
        """Validate an OIDC ID token, including signature and standard claims."""
        if self.provider_profile() != "oidc":
            return {}
        if not id_token:
            raise ValueError("OIDC provider 未返回 id_token")
        metadata = await self.get_provider_metadata()
        jwks_uri = metadata.get("jwks_uri")
        if not jwks_uri:
            raise ValueError("OIDC discovery 未提供 jwks_uri")
        if self._jwks_cache is None:
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                response = await client.get(jwks_uri)
                response.raise_for_status()
                self._jwks_cache = response.json()
        header = jwt.get_unverified_header(id_token)
        supported = metadata.get("id_token_signing_alg_values_supported") or ["RS256"]
        if header.get("alg") not in supported or header.get("alg") == "none":
            raise ValueError("OIDC id_token 使用了不受信任的签名算法")
        jwk = next(
            (
                item
                for item in self._jwks_cache.get("keys", [])
                if item.get("kid") == header.get("kid")
            ),
            None,
        )
        if not jwk:
            self._jwks_cache = None
            raise ValueError("OIDC id_token 的签名密钥不存在")
        claims = jwt.decode(
            id_token,
            key=jwt.PyJWK.from_dict(jwk).key,
            algorithms=[header["alg"]],
            audience=settings.auth_client_id,
            issuer=metadata.get("issuer") or settings.auth_issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
        if expected_nonce and claims.get("nonce") != expected_nonce:
            raise ValueError("OIDC nonce 校验失败")
        return claims

    async def fetch_userinfo(self, access_token: str) -> dict[str, Any]:
        metadata = await self.get_provider_metadata()
        endpoint = metadata.get("userinfo_endpoint")
        if not endpoint:
            raise ValueError("userinfo_endpoint 未配置")
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            response = await client.get(
                endpoint, headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _claim_is_true(value: Any, expected: str = "true") -> bool:
        return str(value).strip().lower() == expected.strip().lower()

    def map_user_claims(self, claims: dict[str, Any]) -> dict[str, Any]:
        if self.provider_profile() == "enterprise_oa":
            return self.map_enterprise_oa_user_claims(claims)
        subject = str(claims.get(settings.auth_user_id_claim) or "")
        email = claims.get(settings.auth_email_claim)
        username = claims.get(settings.auth_username_claim) or email or subject
        groups = self.normalize_groups(
            claims.get(settings.auth_groups_claim) or [], settings.auth_groups_separator
        )
        verified_claim = settings.auth_email_verified_claim.strip()
        verified = bool(verified_claim) and self._claim_is_true(
            claims.get(verified_claim), settings.auth_email_verified_value
        )
        return {
            "provider": settings.auth_provider_name,
            "subject": subject,
            "username": str(username),
            "email": self.normalize_email(str(email)) if email else None,
            "email_verified": verified,
            "display_name": claims.get(settings.auth_display_name_claim) or username,
            "avatar_url": claims.get(settings.auth_avatar_claim),
            "groups": ",".join(groups),
            "role": self.resolve_role(
                str(username), str(email) if email else None, groups
            ),
        }

    def map_enterprise_oa_user_claims(self, claims: dict[str, Any]) -> dict[str, Any]:
        subject = str(claims.get("sub") or claims.get("englishName") or "")
        username = str(claims.get("englishName") or subject)
        email = claims.get("email")
        groups = self.normalize_groups(claims.get("deptPath"), "/")
        for field in ("businessId", "businessName", "deptId", "deptName", "emplClass"):
            if claims.get(field):
                groups.append(str(claims[field]))
        return {
            "provider": settings.auth_provider_name,
            "subject": subject,
            "username": username,
            "email": self.normalize_email(str(email)) if email else None,
            "email_verified": self._claim_is_true(claims.get("email_verified")),
            "display_name": claims.get("displayName")
            or claims.get("chineseName")
            or username,
            "avatar_url": claims.get("picture"),
            "groups": ",".join(dict.fromkeys(groups)),
            "role": self.resolve_role(username, str(email) if email else None, groups),
        }

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def normalize_groups(groups_value: Any, separator: str = ",") -> list[str]:
        if isinstance(groups_value, str):
            return [
                item.strip()
                for item in groups_value.split(separator or ",")
                if item.strip()
            ]
        if groups_value is None:
            return []
        return [str(item) for item in groups_value if str(item)]

    def resolve_role(self, username: str, email: str | None, groups: list[str]) -> str:
        admin_groups = set(settings.csv_list(settings.auth_admin_groups))
        admin_users = set(settings.csv_list(settings.auth_admin_users))
        if (
            admin_groups.intersection(groups)
            or username in admin_users
            or (email and email in admin_users)
        ):
            return "admin"
        return "user"

    def has_users(self) -> bool:
        if not db_manager:
            return False
        with db_manager.session_scope() as session:
            return session.exec(select(AuthUser.id).limit(1)).first() is not None

    def has_local_password_users(self) -> bool:
        """Return whether at least one active local login credential exists."""
        if not db_manager:
            return False
        with db_manager.session_scope() as session:
            statement = (
                select(AuthUser.id)
                .where(AuthUser.password_hash.is_not(None))
                .where(AuthUser.is_active == True)
                .limit(1)
            )
            return session.exec(statement).first() is not None

    def hash_password(self, password: str) -> str:
        if len(password) < 10:
            raise ValueError("密码至少需要 10 个字符")
        return self._password_hasher.hash(password)

    def verify_password(self, password_hash: str | None, password: str) -> bool:
        if not password_hash:
            return False
        try:
            return self._password_hasher.verify(password_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            return False

    def create_initial_admin(
        self, username: str, email: str, password: str
    ) -> AuthUser:
        if self.has_local_password_users():
            raise ValueError("本地登录已完成初始化")
        return self.create_local_user(
            username, email, password, role="admin", temporary=False
        )

    def create_local_user(
        self,
        username: str,
        email: str,
        password: str,
        *,
        role: str = "user",
        temporary: bool = True,
    ) -> AuthUser:
        if not db_manager:
            raise RuntimeError("数据库连接不可用")
        username = username.strip()
        email = self.normalize_email(email)
        if not username or not email:
            raise ValueError("用户名和邮箱不能为空")
        if role not in {"user", "admin"}:
            raise ValueError("无效角色")
        with db_manager.session_scope() as session:
            if session.exec(
                select(AuthUser).where(AuthUser.username == username)
            ).first():
                raise ValueError("用户名已存在")
            if session.exec(select(AuthUser).where(AuthUser.email == email)).first():
                raise ValueError("邮箱已存在")
            user = AuthUser(
                provider="local",
                subject=f"local:{username}",
                username=username,
                email=email,
                email_verified=True,
                display_name=username,
                role=role,
                password_hash=self.hash_password(password),
                must_change_password=temporary,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)
            return user

    def authenticate_local(self, login: str, password: str) -> AuthUser | None:
        if not db_manager:
            return None
        normalized = self.normalize_email(login)
        with db_manager.session_scope() as session:
            statement = select(AuthUser).where(
                (AuthUser.username == login.strip()) | (AuthUser.email == normalized)
            )
            user = session.exec(statement).first()
            if (
                not user
                or not user.is_active
                or not self.verify_password(user.password_hash, password)
            ):
                return None
            user.last_login_at = datetime.now()
            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)
            return user

    def login_rate_limited(self, key: str) -> bool:
        """Allow at most five failed local logins per key in five minutes."""
        now = time.monotonic()
        recent = [
            stamp for stamp in self._login_failures.get(key, []) if now - stamp < 300
        ]
        self._login_failures[key] = recent
        return len(recent) >= 5

    def record_login_failure(self, key: str) -> None:
        self._login_failures.setdefault(key, []).append(time.monotonic())

    def clear_login_failures(self, key: str) -> None:
        self._login_failures.pop(key, None)

    def change_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> None:
        if not db_manager:
            raise RuntimeError("数据库连接不可用")
        with db_manager.session_scope() as session:
            user = session.get(AuthUser, user_id)
            if not user or not self.verify_password(
                user.password_hash, current_password
            ):
                raise ValueError("当前密码不正确")
            user.password_hash = self.hash_password(new_password)
            user.must_change_password = False
            user.updated_at = datetime.now()
            session.add(user)

    def list_users(self) -> list[AuthUser]:
        if not db_manager:
            return []
        with db_manager.session_scope() as session:
            users = session.exec(
                select(AuthUser).order_by(AuthUser.created_at.desc())
            ).all()
            for user in users:
                session.expunge(user)
            return list(users)

    def create_user_with_temporary_password(
        self, username: str, email: str, role: str = "user"
    ) -> tuple[AuthUser, str]:
        password = secrets.token_urlsafe(12)
        return self.create_local_user(
            username, email, password, role=role, temporary=True
        ), password

    def update_user_access(
        self, user_id: int, *, role: str | None = None, is_active: bool | None = None
    ) -> AuthUser:
        if not db_manager:
            raise RuntimeError("数据库连接不可用")
        if role is not None and role not in {"user", "admin"}:
            raise ValueError("无效角色")
        with db_manager.session_scope() as session:
            user = session.get(AuthUser, user_id)
            if not user:
                raise ValueError("用户不存在")
            removes_admin = user.role == "admin" and (
                role == "user" or is_active is False
            )
            if removes_admin:
                active_admins = session.exec(
                    select(AuthUser)
                    .where(AuthUser.role == "admin")
                    .where(AuthUser.is_active == True)
                ).all()
                if len(active_admins) <= 1:
                    raise ValueError("不能移除最后一个启用的管理员")
            if role is not None:
                user.role = role
            if is_active is not None:
                user.is_active = is_active
            user.updated_at = datetime.now()
            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)
            return user

    def reset_user_password(self, user_id: int) -> str:
        if not db_manager:
            raise RuntimeError("数据库连接不可用")
        password = secrets.token_urlsafe(12)
        with db_manager.session_scope() as session:
            user = session.get(AuthUser, user_id)
            if not user:
                raise ValueError("用户不存在")
            user.password_hash = self.hash_password(password)
            user.must_change_password = True
            user.updated_at = datetime.now()
            session.add(user)
        return password

    def upsert_external_user(self, user_data: dict[str, Any]) -> AuthUser:
        """Resolve identity first, then safely link a verified unique email."""
        if not db_manager:
            raise RuntimeError("数据库连接不可用")
        provider, subject = user_data["provider"], user_data["subject"]
        now = datetime.now()
        with db_manager.session_scope() as session:
            identity = session.exec(
                select(AuthIdentity)
                .where(AuthIdentity.provider == provider)
                .where(AuthIdentity.subject == subject)
            ).first()
            user = session.get(AuthUser, identity.user_id) if identity else None
            if not user and not identity:
                user = session.exec(
                    select(AuthUser)
                    .where(AuthUser.provider == provider)
                    .where(AuthUser.subject == subject)
                ).first()
            email = user_data.get("email")
            if not user and email and user_data.get("email_verified"):
                matches = session.exec(
                    select(AuthUser).where(AuthUser.email == email)
                ).all()
                if len(matches) > 1:
                    logger.warning("拒绝绑定存在多个本地账号的已验证邮箱")
                    raise ValueError("邮箱对应多个账号，请联系管理员")
                user = matches[0] if matches else None
            if not user:
                user = AuthUser(
                    **user_data, created_at=now, updated_at=now, last_login_at=now
                )
            else:
                for field in (
                    "username",
                    "email",
                    "email_verified",
                    "display_name",
                    "avatar_url",
                    "groups",
                ):
                    value = user_data.get(field)
                    if value is not None:
                        setattr(user, field, value)
                if user.role != "admin":
                    user.role = user_data.get("role", user.role)
                user.updated_at = now
                user.last_login_at = now
            session.add(user)
            session.commit()
            session.refresh(user)
            if not identity:
                identity = AuthIdentity(
                    user_id=user.id, provider=provider, subject=subject, email=email
                )
                session.add(identity)
            else:
                identity.email = email
                identity.updated_at = now
                session.add(identity)
            session.commit()
            session.refresh(user)
            session.expunge(user)
            return user

    def get_user(self, user_id: int | None) -> AuthUser | None:
        if not user_id or not db_manager:
            return None
        with db_manager.session_scope() as session:
            user = session.get(AuthUser, user_id)
            if not user or not user.is_active:
                return None
            session.expunge(user)
            return user

    def user_to_dict(self, user: AuthUser | None) -> dict[str, Any] | None:
        if not user:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "groups": settings.csv_list(user.groups or ""),
            "role": user.role,
            "must_change_password": user.must_change_password,
            "last_login_at": user.last_login_at.isoformat()
            if user.last_login_at
            else None,
        }

    def _jwt_secret(self) -> str:
        secret = settings.auth_jwt_secret or settings.storage_secret
        if not secret:
            raise RuntimeError("AUTH_JWT_SECRET 或 STORAGE_SECRET 未配置")
        if len(secret.encode()) < 32:
            raise RuntimeError("JWT 密钥至少需要 32 字节")
        return secret

    def _jwt_algorithm(self) -> str:
        algorithm = settings.auth_jwt_algorithm.upper()
        if algorithm not in {"HS256", "HS384", "HS512"}:
            raise RuntimeError("AUTH_JWT_ALGORITHM 仅支持 HS256/HS384/HS512")
        return algorithm

    def issue_web_token(self, user: AuthUser) -> str:
        now = datetime.now(UTC)
        claims = {
            "sub": str(user.id),
            "role": user.role,
            "type": "web",
            "iss": settings.auth_jwt_issuer,
            "aud": settings.auth_jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=settings.auth_jwt_expires_minutes),
            "jti": secrets.token_urlsafe(16),
        }
        return jwt.encode(claims, self._jwt_secret(), algorithm=self._jwt_algorithm())

    def authenticate_web_token_context(
        self, token: str
    ) -> tuple[AuthUser, set[str]] | None:
        try:
            claims = jwt.decode(
                token,
                self._jwt_secret(),
                algorithms=[self._jwt_algorithm()],
                audience=settings.auth_jwt_audience,
                issuer=settings.auth_jwt_issuer,
                options={"require": ["sub", "iat", "exp", "jti"]},
            )
            if claims.get("type") != "web":
                return None
            user = self.get_user(int(claims["sub"]))
            if not user:
                return None
            scopes = {"tool:read", "tool:preview"}
            if user.role == "admin":
                scopes.add("*")
            return user, scopes
        except (jwt.PyJWTError, ValueError, TypeError):
            return None

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def create_personal_token(
        self,
        user_id: int,
        name: str = "default",
        expires_at: datetime | None = None,
    ) -> dict[str, Any]:
        if not db_manager:
            raise RuntimeError("数据库连接不可用")
        token = generate_auth_token()
        with db_manager.session_scope() as session:
            user = session.get(AuthUser, user_id)
            if not user or not user.is_active:
                raise ValueError("用户不存在或已禁用")
            record = AuthToken(
                user_id=user_id,
                name=name,
                token_hash=self.hash_token(token),
                token_prefix=token[:12],
                expires_at=expires_at,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return {
                "id": record.id,
                "name": record.name,
                "token": token,
                "token_prefix": record.token_prefix,
                "created_at": record.created_at.isoformat(),
            }

    def start_device_authorization(self, token_env: str) -> dict[str, Any]:
        if not db_manager:
            raise RuntimeError("数据库连接不可用")
        if not re.fullmatch(r"NICETOOL(?:_[A-Z0-9]+)*_TOKEN", token_env):
            raise ValueError("Token 环境变量必须是 NICETOOL_*_TOKEN")
        device_code = secrets.token_urlsafe(32)
        user_code = secrets.token_hex(4).upper()
        record = AuthDeviceAuthorization(
            device_code_hash=self.hash_token(device_code),
            user_code=user_code,
            token_env=token_env,
            expires_at=datetime.now() + timedelta(minutes=10),
        )
        with db_manager.session_scope() as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            record_id = record.id
        return {
            "id": record_id,
            "device_code": device_code,
            "user_code": user_code,
            "expires_in": 600,
            "interval": 2,
        }

    def approve_device_authorization(self, user_code: str, user_id: int) -> bool:
        if not db_manager:
            return False
        with db_manager.session_scope() as session:
            record = session.exec(
                select(AuthDeviceAuthorization).where(
                    AuthDeviceAuthorization.user_code == user_code.strip().upper()
                )
            ).first()
            if (
                not record
                or record.status != "pending"
                or record.expires_at < datetime.now()
            ):
                return False
            user = session.get(AuthUser, user_id)
            if not user or not user.is_active:
                return False
            record.status = "approved"
            record.user_id = user_id
            session.add(record)
            return True

    def exchange_device_authorization(self, device_code: str) -> dict[str, Any]:
        if not db_manager:
            return {"status": "invalid_grant"}
        with db_manager.session_scope() as session:
            record = session.exec(
                select(AuthDeviceAuthorization)
                .where(
                    AuthDeviceAuthorization.device_code_hash
                    == self.hash_token(device_code)
                )
                .with_for_update()
            ).first()
            if not record or record.expires_at < datetime.now():
                return {"status": "invalid_grant"}
            if record.status != "approved" or not record.user_id:
                return {"status": "authorization_pending"}
            user = session.get(AuthUser, record.user_id)
            if not user or not user.is_active:
                return {"status": "invalid_grant"}
            token = generate_auth_token()
            session.add(
                AuthToken(
                    user_id=user.id,
                    name="installer",
                    token_hash=self.hash_token(token),
                    token_prefix=token[:12],
                )
            )
            token_env = record.token_env
            session.delete(record)
            return {"status": "approved", "token": token, "token_env": token_env}

    def list_personal_tokens(self, user_id: int) -> list[dict[str, Any]]:
        if not user_id or not db_manager:
            return []
        with db_manager.session_scope() as session:
            records = session.exec(
                select(AuthToken)
                .where(AuthToken.user_id == user_id)
                .order_by(AuthToken.created_at.desc())
            ).all()
            return [
                {
                    "id": item.id,
                    "name": item.name,
                    "token_prefix": item.token_prefix,
                    "is_active": item.is_active,
                    "created_at": item.created_at.isoformat()
                    if item.created_at
                    else None,
                    "last_used_at": item.last_used_at.isoformat()
                    if item.last_used_at
                    else None,
                    "expires_at": item.expires_at.isoformat()
                    if item.expires_at
                    else None,
                }
                for item in records
            ]

    def revoke_personal_token(self, user_id: int, token_id: int) -> bool:
        if not db_manager:
            return False
        with db_manager.session_scope() as session:
            record = session.exec(
                select(AuthToken)
                .where(AuthToken.id == token_id)
                .where(AuthToken.user_id == user_id)
            ).first()
            if not record:
                return False
            record.is_active = False
            session.add(record)
            return True

    def authenticate_personal_token_context(
        self, token: str
    ) -> tuple[AuthUser, set[str]] | None:
        if not token or not settings.auth_enable_personal_tokens or not db_manager:
            return None
        now = datetime.now()
        with db_manager.session_scope() as session:
            record = session.exec(
                select(AuthToken)
                .where(AuthToken.token_hash == self.hash_token(token))
                .where(AuthToken.is_active == True)
            ).first()
            if not record or (record.expires_at and record.expires_at < now):
                return None
            user = session.get(AuthUser, record.user_id)
            if not user or not user.is_active:
                return None
            record.last_used_at = now
            session.add(record)
            session.expunge(user)
            return user, set(ALL_TOOL_SCOPES)

    def authenticate_bearer_token_context(
        self, token: str
    ) -> tuple[AuthUser, set[str]] | None:
        return self.authenticate_web_token_context(
            token
        ) or self.authenticate_personal_token_context(token)

    def authenticate_bearer_token(self, token: str) -> AuthUser | None:
        context = self.authenticate_bearer_token_context(token)
        return context[0] if context else None


auth_service = AuthService()
