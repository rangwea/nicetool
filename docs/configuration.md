# 配置参考

[返回文档索引](README.md)

配置由 `core/settings.py` 的 Pydantic Settings 读取，环境变量名不区分大小写。进程环境变量优先于 dotenv 文件；修改启动配置后需要重启服务。

## 配置文件选择

- 设置 `ENV_FILE` 时，读取指定文件；支持逗号分隔的多个路径，后面的文件覆盖前面的值。
- 未设置 `ENV_FILE` 时，先读取 `.env`，再读取 `.env.${ENV_TYPE}`。
- `ENV_TYPE` 默认 `prod`，仅接受 `dev`、`uat`、`prod`；对应文件不存在时不会自动生成。
- 仓库仍保留 `.env.dev`。若只想加载 `.env`，使用 `ENV_FILE=.env uv run main.py`。

不要将 Server 的 `ENV_TYPE` 与 CLI 的 `--env` 混淆：前者选择服务启动配置，后者选择远端实例。

## 服务与数据库

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `8000` | 监听端口 |
| `PROJECT_PATH` | 空 | URL 挂载前缀，例如 `/nicetool` |
| `LANGUAGE` | `zh-CN` | 在 `.env` 配置的全局界面语言，支持 `zh-CN` / `en-US`；修改后重启生效 |
| `STORAGE_SECRET` | 内置开发值 | 会话存储密钥，部署时替换 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `TOOLS_DIR` | `./tools` | 可重建的工具运行缓存目录 |
| `MYSQL_HOST` | `localhost` | 平台数据库主机 |
| `MYSQL_PORT` | `3306` | 平台数据库端口 |
| `MYSQL_USER` | `root` | 数据库用户 |
| `MYSQL_PASSWORD` | 空 | 数据库密码 |
| `MYSQL_DATABASE` | `nicetool` | 已创建的数据库名 |
| `MYSQL_CHARSET` | `utf8mb4` | 连接字符集 |
| `MYSQL_POOL_SIZE` | `10` | 常驻连接池大小 |
| `MYSQL_MAX_OVERFLOW` | `20` | 额外连接数上限 |
| `MYSQL_POOL_TIMEOUT` | `30` | 等待连接的超时秒数 |
| `MYSQL_POOL_RECYCLE` | `3600` | 连接回收周期秒数 |
| `REQUEST_TIMEOUT` | `30` | 认证 HTTP 请求超时秒数 |

平台 MySQL 保存工具版本、账号和管理配置。工具访问的业务数据源在管理后台单独配置，不通过这些 `MYSQL_*` 变量选择。

## 登录

`AUTH_ENABLED` 默认 `false`。启用后配置 `AUTH_JWT_SECRET`；HTTPS 部署设置 `AUTH_REQUIRE_HTTPS_COOKIE=true`。完整配置见[认证与权限](oauth2-auth.md)。

## 样式与配置入口

平台使用 `core/styles.py` 的固定样式，没有主题切换和通用设置保存页面。服务配置通过环境变量管理；数据源、变量、枚举和客户端环境通过各自的后台页面管理。
