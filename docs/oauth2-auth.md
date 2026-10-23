# 认证与项目权限

[返回文档索引](README.md)

## 本地账号

```dotenv
AUTH_ENABLED=true
AUTH_JWT_SECRET=replace-with-a-random-secret
AUTH_JWT_EXPIRES_MINUTES=30
AUTH_REQUIRE_HTTPS_COOKIE=false
```

没有本地密码账号时，`/auth/login` 提供管理员初始化。之后由管理员创建用户，临时密码需要首次登录后修改。网页使用 HttpOnly Cookie 保存短期 JWT；到期后重新登录，不提供 Refresh Token。HTTPS 部署将 `AUTH_REQUIRE_HTTPS_COOKIE` 设为 `true`。

认证默认关闭。关闭时不应用通常的用户和项目访问限制，适合本机调试，不应当作多用户权限配置。

## OIDC

```dotenv
AUTH_PROVIDER_PROFILE=oidc
AUTH_PROVIDER_NAME=example-sso
AUTH_ISSUER=https://id.example.com
AUTH_CLIENT_ID=replace-with-client-id
AUTH_CLIENT_SECRET=replace-with-client-secret
AUTH_REDIRECT_URI=https://tools.example.com/auth/callback
AUTH_SCOPES="openid profile email"
```

服务通过 discovery 获取元数据，通过 JWKS 校验 ID Token。配置了客户端 ID 与密钥后，登录页提供外部登录入口。子路径部署时回调 URL 也要包含前缀。

## OAuth2

```dotenv
AUTH_PROVIDER_PROFILE=oauth2
AUTH_PROVIDER_NAME=example-oauth
AUTH_AUTHORIZATION_ENDPOINT=https://id.example.com/oauth/authorize
AUTH_TOKEN_ENDPOINT=https://id.example.com/oauth/token
AUTH_USERINFO_ENDPOINT=https://id.example.com/api/user
AUTH_CLIENT_ID=replace-with-client-id
AUTH_CLIENT_SECRET=replace-with-client-secret
AUTH_REDIRECT_URI=https://tools.example.com/auth/callback
AUTH_SCOPES="profile email"
```

通用 OAuth2 需要三个显式端点。字段通过 `AUTH_USER_ID_CLAIM`、`AUTH_USERNAME_CLAIM`、`AUTH_EMAIL_CLAIM`、`AUTH_DISPLAY_NAME_CLAIM` 和 `AUTH_GROUPS_CLAIM` 映射。仅可信邮箱验证字段匹配时才按邮箱绑定已有账号。

源码还支持 `enterprise_oa` 专用字段适配，使用 `AUTH_ENTERPRISE_OA_BASE_URL`；新接入优先使用通用配置。企业网关 X-Token 登录已移除。

## 权限模型

权限分成项目范围与操作范围：

| 账号 | 项目范围 | 默认生命周期操作 |
| --- | --- | --- |
| 管理员 | 全部项目 | 读取、预览、发布、回滚、删除、管理 |
| 普通用户 | 管理员分配的项目 | 读取、预览 |

管理员在用户管理中整体设置普通用户的项目授权；未授权的普通用户不能浏览对应正式工具。Token 还受签发的 scope 限制，项目授权不是发布授权。

`AUTH_ADMIN_USERS` 和 `AUTH_ADMIN_GROUPS` 用于外部登录角色判定。`AUTH_PROTECTED_PATHS`、`AUTH_ADMIN_PATHS`、`AUTH_PUBLIC_PATHS` 调整路径保护，修改时应核对中间件逻辑。

## CLI 与设备授权

CLI 使用 Bearer 个人 Token；安装脚本可打开浏览器，经用户确认后获取凭据。Token 可撤销，服务端保存哈希。见[Token 配置](nicetool-token-setup.md)。

```bash
AUTH_ADMIN_GROUPS=nicetool,platform-admin
AUTH_ADMIN_USERS=alice@example.com,bob
AUTH_PROTECTED_PATHS=/user,/admin,/api
AUTH_ADMIN_PATHS=/admin
AUTH_PUBLIC_PATHS=/,/health,/docs,/redoc,/openapi.json,/auth,/api/auth/device/start,/api/auth/device/token,/client/tool
```

设备授权使用 `/api/auth/device/start` 发起授权、`/api/auth/device/token` 轮询结果。若部署中显式设置了 `AUTH_PUBLIC_PATHS`，需同时加入这两个匿名访问路径。浏览器确认页仍为 `/auth/device/authorize`，需要登录；安装脚本使用安装服务下发的环境 URL（含 HTTPS 和部署前缀）拼接浏览器授权链接；目标环境的授权接口无需配置环境列表。

项目访问控制不替代业务数据库权限。工具代码在服务进程内运行，发布账号应限于可信开发者。
