# Configuration Reference

NiceTool reads runtime configuration from `.env` through `pydantic-settings`.

## Service and database

| Variable | Default | Description |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Listen address. |
| `PORT` | `8000` | Listen port. |
| `PROJECT_PATH` | empty | Optional URL mount prefix. |
| `LANGUAGE` | `zh-CN` | Global UI language, `zh-CN` or `en-US`. Restart required. |
| `STORAGE_SECRET` | development value | NiceGUI storage secret. Replace in production. |
| `LOG_LEVEL` | `INFO` | Log level. |
| `TOOLS_DIR` | `./tools` | Rebuildable tool runtime cache directory. |
| `MYSQL_HOST` | `localhost` | Platform database host. |
| `MYSQL_PORT` | `3306` | Platform database port. |
| `MYSQL_USER` | `root` | Database user. |
| `MYSQL_PASSWORD` | empty | Database password. |
| `MYSQL_DATABASE` | `nicetool` | Existing database name. |
| `MYSQL_CHARSET` | `utf8mb4` | Connection charset. |

The platform MySQL database stores tool versions, accounts, and administration configuration. Business data sources used by tools are configured separately in the admin console.

## Authentication

`AUTH_ENABLED` defaults to `false`. When enabled, configure `AUTH_JWT_SECRET`. For HTTPS deployments, set `AUTH_REQUIRE_HTTPS_COOKIE=true`.
