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

## Configuration file selection

Process environment variables override dotenv values. Names are case-insensitive. Restart after changing startup configuration.

- `ENV_FILE` selects one or more comma-separated paths; later files override earlier ones.
- Without `ENV_FILE`, the server loads `.env`, then `.env.${ENV_TYPE}`.
- `ENV_TYPE` defaults to `prod`; supported values are `dev`, `uat` and `prod`. Missing files are not created automatically.
- Use `ENV_FILE=.env uv run main.py` to load only `.env`.

Server `ENV_TYPE` selects startup configuration. CLI `--env` selects a remote instance from client configuration; these are separate settings.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DEBUG` | `false` | Debug mode. |
| `MYSQL_POOL_SIZE` | `10` | Persistent pool connections. |
| `MYSQL_MAX_OVERFLOW` | `20` | Additional pool connections. |
| `MYSQL_POOL_TIMEOUT` | `30` | Seconds waiting for a connection. |
| `MYSQL_POOL_RECYCLE` | `3600` | Seconds before recycling a connection. |
| `REQUEST_TIMEOUT` | `30` | Authentication HTTP timeout in seconds. |

Authentication supports local accounts, OIDC and OAuth2; see [Authentication and permissions](oauth2-auth.md). Application styling is fixed in `core/styles.py`; there is no theme preference or generic settings-save page.
