# User and Admin Guide

NiceTool has two main user surfaces: the tool center for business users and the admin console for platform administrators.

## Tool users

Users open the tool center, search or filter tools, and run tools that they are allowed to access. Tools may provide forms, query pages, dashboards, exports, and logs depending on their implementation.

## Administrators

Administrators manage users, project access, tools, data sources, variables, enums, CLI environments, and preview logs.

## Tool lifecycle

1. Create or update a tool source file.
2. Preview it and validate behavior.
3. Publish a version.
4. Make it available to users by project access.
5. Inspect history and logs when troubleshooting.

## Language

The application language is configured in `.env` with `LANGUAGE`. Supported values are `zh-CN` and `en-US`. Restart the server after changing it.
