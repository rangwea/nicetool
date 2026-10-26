# Deployment Guide

## Local startup

Install Python 3.13+, uv and MySQL as described in the [quick start](../README.en.md). Create the database, configure `.env`, then run:

```bash
uv sync --locked
uv run main.py
```

Startup creates missing tables; it does not alter existing columns or indexes.

## Docker

The repository `Dockerfile` builds an application image containing the source and locked dependencies in `/opt/venv`.

```bash
docker build -t nicetool .
docker run -d --name nicetool --env-file .env -p 8000:8000 \
  -v nicetool-logs:/app/logs \
  -v nicetool-previews:/tmp/nicegui_client_tools nicetool
```

`.dockerignore` excludes real `.env` files; provide configuration at runtime. The health check follows `PORT` and `PROJECT_PATH`.

Inside a container, `localhost` refers to that container. Use a database service name on the same Docker network or a host address supported by your Docker installation.

## Persistence and recovery

| Data | Storage | Recovery |
| --- | --- | --- |
| Published tool source, versions, accounts and configuration | MySQL | Database backup |
| Tool runtime files | `TOOLS_DIR` | Rebuilt from MySQL |
| Preview source and logs | `/tmp/nicegui_client_tools` | Preview again or persist a volume |
| Application and tool logs | `logs/` | Persist a volume or use external logging |

Backing up only `tools/` cannot restore the platform. Keep database backups and runtime configuration and secrets separately.

## Reverse proxy and subpaths

For `PROJECT_PATH=/nicetool`, preserve the prefix and support WebSockets. Forward the external host and protocol. OAuth callback URLs must include the prefix, for example `https://tools.example.com/nicetool/auth/callback`.

Set independent `STORAGE_SECRET` and `AUTH_JWT_SECRET` values. Enable authentication for shared deployments and use `AUTH_REQUIRE_HTTPS_COOKIE=true` over HTTPS.

## Upgrades and execution boundary

Back up the database and configuration, record the current version, review schema changes, stop the old instance and apply verified migrations before starting the new image. `scripts/init.sql` is a complete schema, not an incremental migration tool. See [Upgrade and recovery](upgrading.md).

Tools execute inside the service process. Grant publishing permissions to trusted developers. Preview files and runtime caches are local; multiple service instances require storage and routing design.

For a disposable first experience, use the [demo](demo.md).
