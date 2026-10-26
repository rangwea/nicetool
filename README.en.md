# NiceTool

[简体中文](README.md) | English

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.13%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![NiceGUI](https://img.shields.io/badge/UI-NiceGUI-5898D4)](https://nicegui.io/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

An all-in-one AI tool platform that turns ideas into tools your team can use.

Describe what you need in natural language, let AI build a tool, preview it in your browser, and publish it to your team's tool center. NiceTool brings together data access, tool creation, previewing, debugging, publishing, version management, and access control, so one-off requests can become tools your team maintains and improves over time.

Users can focus on the task and whether the results are correct. Creators describe requirements and refine tools through an AI coding assistant with the NiceTool Skill installed; team members use published tools directly in their browser.

## From an idea to a working tool

1. **Describe the task**: Tell your AI assistant which data to query, what actions to perform, and how to present the results.
2. **Generate a tool**: The assistant uses project context, configured data sources, and development conventions to build it.
3. **Preview and refine**: Open the preview, request changes in natural language, and let the assistant inspect logs to troubleshoot issues.
4. **Publish and share**: Publish the verified tool to the tool center and grant project access to the members who need it.
5. **Keep improving**: Iterate on feedback and use versions and logs to support ongoing maintenance.

An external AI coding assistant and the NiceTool Skill create and modify tools. NiceTool provides the runtime, previews, publishing, and team administration.

## What can you build?

| Use case | Examples |
| --- | --- |
| Data queries | Filter records by order number, status, and date, with paginated results |
| Business operations | Build maintenance forms, batch processing tools, and everyday admin utilities |
| Analytics | Summarize business metrics, create charts and dashboards, and export reports |
| Team collaboration | Publish tools centrally, assign project permissions, and provide a shared entry point |

## Platform capabilities

- **AI-assisted creation**: Turn natural-language requirements into tools with the NiceTool Skill, then refine and debug them through follow-up requests.
- **Publishing workflow**: Preview and verify tools before publishing, with version history, rollback, and logs.
- **Unified tool center**: Organize tools by project and browse, search, filter, and run them in one place.
- **Shared data resources**: Manage MySQL and MongoDB data sources, platform variables, and enums for tools to reuse.
- **Team access management**: Support built-in accounts, OIDC/OAuth2, personal tokens, and per-user project permissions.
- **Read-only analytics**: Use the NiceTool Skill for queries, charts, dashboards, and exports with explicit row limits.

## Try the demo

With Docker and Compose v2 installed, start a complete demo with synthetic data:

```bash
sh scripts/demo.sh
```

Open the [tool center](http://localhost:8000/user) to try an order query, sales dashboard, and quote calculator. You do not need to install Python, prepare a database, or configure a model API key.

Then follow the [complete AI creation walkthrough](docs/en/demo.md) to have your assistant build, refine, and publish a new tool. The demo is accessible only from your local machine and uses synthetic data throughout.

## Create your first AI tool

If you already have a NiceTool instance, [install the NiceTool Skill](docs/en/nicetool-skill.md) in your working project and authorize your account. Then describe your requirements to an AI coding assistant that supports Skills:

> Create an order query tool using the configured order data source. Support filtering by order number, date, and status, and display paginated results. Generate a preview first; do not publish it.

Open the preview URL returned by the assistant, verify the result, and request improvements:

> Add an order amount summary and let me export the current filtered results, up to 1,000 rows.

Once you have verified the tool and the target instance, publish it:

> Publish the verified tool to the orders project and check its published state.

After an administrator grants project access, members can open the tool from the tool center. End users do not need a development environment or programming experience. Publishing requires the appropriate permissions; see [development task examples](docs/en/nicetool-skill-usage.md) for more prompts.

## Deploy your own platform

Prepare Python 3.13+, uv, and an accessible MySQL instance. After downloading this repository, run the following from its root:

```bash
uv sync --locked
```

Create a MySQL database and grant the application account permission to create tables and read and write data in it:

```sql
CREATE DATABASE nicetool CHARACTER SET utf8mb4;
```

Use `.env.example` as a reference to create or edit the root `.env` file. Replace the example values below with your local settings. Back up an existing `.env` before changing it:

```dotenv
HOST=0.0.0.0
PORT=8000
LANGUAGE=en-US
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=nicetool
MYSQL_PASSWORD=replace-with-your-password
MYSQL_DATABASE=nicetool
STORAGE_SECRET=replace-with-a-random-secret
AUTH_ENABLED=true
AUTH_JWT_SECRET=replace-with-another-random-secret
```

Generate secrets with `uv run python -c "import secrets; print(secrets.token_urlsafe(32))"`. Do not commit actual credentials to version control. Set `LANGUAGE=en-US` in `.env` to use the English interface; see [internationalization](docs/en/internationalization.md) for details.

```bash
uv run main.py
```

On startup, the application creates missing tables and restores tool caches from the database. Visit the [login page](http://localhost:8000/auth/login) to initialize the administrator account, then use the [admin console](http://localhost:8000/admin) to configure users and data sources.

| Entry point | Default URL |
| --- | --- |
| Home | <http://localhost:8000> |
| Tool center | <http://localhost:8000/user> |
| Admin console | <http://localhost:8000/admin> |
| API documentation | <http://localhost:8000/docs> |
| Health check | <http://localhost:8000/health> |

### Docker deployment

```bash
docker build -t nicetool .
docker run -d --name nicetool --env-file .env -p 8000:8000 nicetool
```

The image includes the platform runtime and installs dependencies with uv using `uv.lock`. Inside the container, `MYSQL_HOST` must point to a database address reachable from that container. The image excludes `.env` and environment-specific configuration; inject settings through environment variables at runtime. See the [deployment guide](docs/en/deployment.md) for persistence, reverse proxy, and upgrade guidance.

## Documentation

Choose a starting point from the [documentation index](docs/en/README.md):

- [Configuration reference](docs/en/configuration.md)
- [User and admin guide](docs/en/user-guide.md)
- [Authentication and project permissions](docs/en/oauth2-auth.md)
- [Tool development](docs/en/tool-development.md)
- [CLI and Skill](docs/en/nicetool-skill.md)
- [API reference](docs/en/api.md)
- [Development and contributing](docs/en/contributing.md)

## Developer notes

The platform uses Python, NiceGUI, FastAPI, and MySQL. Tool source versions are stored in the database, and `tools/` is a rebuildable runtime cache. Tool code executes within the service process, so publishing permissions should be granted to trusted developers.

For manual tool development, platform extensions, or API integration, see [tool development](docs/en/tool-development.md), the [API reference](docs/en/api.md), and the [contributing guide](docs/en/contributing.md).

## Contributing

Issue reports, documentation improvements, and focused code changes are welcome. Include reproduction steps, version information, and sanitized logs when reporting an issue. Add tests and migration notes for behavior changes. The project uses uv for dependency management; see the [contributing guide](docs/en/contributing.md) for commands.

## Topics

`python` · `nicegui` · `fastapi` · `ai-tools` · `ai-agent` · `internal-tools` · `low-code` · `tool-management` · `self-hosted` · `mysql` · `mongodb` · `developer-tools`

## License

This project is licensed under the [MIT License](LICENSE). Copyright © 2026 wikia.
