# 部署指南

[返回文档索引](README.md)

## 本地运行

按照[快速开始](../README.zh-CN.md)准备 Python 3.13+、uv 和 MySQL。执行 `uv sync --locked` 安装锁定依赖，再执行 `uv run main.py`。MySQL 数据库需预先创建；启动建表只创建缺失的表，不负责变更已有表的列或索引。

## Docker

仓库的 `Dockerfile` 构建包含源码的应用镜像，使用 uv 安装锁定依赖到 `/opt/venv`，通过该环境的 Python 启动服务。

```bash
docker build -t nicetool .
docker run -d --name nicetool   --env-file .env   -p 8000:8000   -v nicetool-logs:/app/logs   -v nicetool-previews:/tmp/nicegui_client_tools   nicetool
```

`.dockerignore` 排除 `.env`、`.env.*` 中的真实配置，仅保留 `.env.example`。运行时使用 `--env-file` 或部署平台的环境变量配置。镜像健康检查使用配置的端口和挂载前缀访问 `/health`。

容器内 `localhost` 指向容器自身。数据库在其他容器时，使用同一 Docker 网络中的服务名；在宿主机时，使用该运行环境支持的宿主机地址。不要直接沿用本机开发的 `MYSQL_HOST=127.0.0.1`。

```bash
docker logs -f nicetool
docker stop nicetool
```

## 数据持久化

| 内容 | 位置 | 恢复方式 |
| --- | --- | --- |
| 工具源码与版本、用户、平台配置 | MySQL | 数据库备份恢复 |
| 正式工具运行文件 | `TOOLS_DIR` | 启动时从数据库恢复 |
| 预览代码与日志 | `/tmp/nicegui_client_tools` | 重新预览或挂载卷 |
| 应用及正式工具日志 | `logs/` | 挂载卷或外部日志系统 |

只备份 `tools/` 不足以恢复平台。应备份 MySQL，并单独保存运行配置及密钥。

## 反向代理与子路径

设置 `PROJECT_PATH=/nicetool` 后，页面、API 和登录回调都包含此前缀。反向代理应保留前缀、支持 WebSocket，并传递正确的外部协议与主机信息。OIDC/OAuth2 的回调地址应与外部 URL 一致，例如 `https://tools.example.com/nicetool/auth/callback`。

HTTPS 部署启用 `AUTH_REQUIRE_HTTPS_COOKIE=true`；本机 HTTP 开发保持 `false`。配置独立的 `STORAGE_SECRET` 和 `AUTH_JWT_SECRET`，再开放受保护入口。

## 升级

1. 备份数据库与运行配置，记录当前代码提交或镜像版本。
2. 检查 `models/`、`scripts/init.sql` 和发布变更，评估已有表的迁移需求。
3. 用新的 `uv.lock` 安装依赖或重建镜像。
4. 停止旧实例，应用经过验证的数据库变更，再启动新实例。
5. 检查 `/health`，并验证登录、工具预览和已发布工具。

`scripts/init.sql` 是完整建表脚本，不是增量迁移工具。回滚涉及数据库结构时，需要与备份配套，不能仅切换代码。

## 已知部署边界

工具模块在服务进程内导入执行，不是沙箱；只允许可信开发者发布。预览文件及运行缓存依赖本地文件系统，多实例部署需要额外设计共享存储和请求路由。

首次体验见[一键演示](demo.md)，详细升级步骤见[升级与恢复](upgrading.md)。
