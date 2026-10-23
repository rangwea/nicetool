# Upgrade and Recovery

This document describes a conservative upgrade path for existing NiceTool instances.

## Before upgrading

1. Back up the MySQL database.
2. Back up tool source files and uploaded configuration.
3. Record the current commit, image tag, and `.env` values.
4. Read release notes for configuration or schema changes.

## Upgrade steps

```bash
git pull
uv sync --locked
uv run main.py
```

For Docker deployments, rebuild the image and restart the container with the same `.env` file.

## Recovery

If startup fails, restore the previous image or commit and the database backup. Check `logs/app.log` and `logs/error.log` for the failing migration, configuration, or dependency.

## Current development contract

The project has not launched. Update the server, CLI, Skill and documentation together without preserving obsolete behavior. Publishing requires uploaded source and tool names are strictly validated; see [API reference](api.md).
