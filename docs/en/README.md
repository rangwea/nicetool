# NiceTool Documentation

NiceTool is an all-in-one AI tool platform for business teams. It is designed to turn tools created by AI Agents into previewable, publishable, permission-aware, and maintainable team applications.

This documentation describes the current repository implementation. Examples use localhost or `example.com` and do not depend on any private deployment environment.

## Start here

For the first experience, read [Demo: what AI can create for you](demo.md). For existing deployments, read [Upgrade and recovery](upgrading.md).

## Core topics

| Document | Purpose |
| --- | --- |
| [CLI and Skill](nicetool-skill.md) | How agents create, preview, publish, and manage tools through the CLI. |
| [Development task examples](nicetool-skill-usage.md) | Example prompts for creating tools with AI. |
| [User and admin guide](user-guide.md) | Daily usage for tool users and administrators. |
| [Configuration](configuration.md) | Runtime settings and `.env` variables. |
| [Deployment](deployment.md) | Docker and production deployment guidance. |
| [Tool development](tool-development.md) | Tool file structure and runtime conventions. |
| [Authentication and permissions](oauth2-auth.md) | OAuth2 login and project access control. |

## Repository layout

The application code lives in `public/`, `service/`, `models/`, `core/`, and `component/`. The static website lives in `website/`. Documentation source files live under `docs/`; English documentation lives under `docs/en/`.

## Historical designs

`docs/plans/` contains historical design notes, not the current configuration or API contract. These notes are retained in the repository and excluded from the website's user documentation. Use current guides and the running instance's OpenAPI schema for integrations.
