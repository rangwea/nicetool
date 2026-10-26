# API Navigation

NiceTool exposes FastAPI routes for tools, data sources, previews, initialization, and client integration.

## API documentation

When the server is running, open:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Common route groups

| Group | Purpose |
| --- | --- |
| `/api/tools` | Tool list, details, previews, publishing, state, logs and deletion. |
| `/api/datasources` | Data source list, details and connection testing. |
| `/client/tool/{token}` | Temporary preview page. |
| `/client/tool/{username}/{tool_name}` | Fixed preview page. |
| `/api/variables` | Variable key metadata. |
| `/api/init.sh`, `/api/install.sh` | Client initialization and Skill installation scripts. |
| `/api/downloads` | Skill archive downloads. |
| `/auth`, `/api/auth/device` | Login, personal tokens and device authorization. |

Use the interactive API pages for exact request and response schemas. Add `PROJECT_PATH` when using a URL prefix. Not every admin operation has a REST endpoint: data source writes and version rollback are handled by admin services, not generic CRUD routes.

Create a temporary preview with `POST /api/tools/preview`, or a fixed preview with `POST /api/tools/preview/{username}/{tool_name}`. Both take JSON with `content`. Fixed preview ownership and the preview scope are checked when authentication is enabled. Preview pages are public by default; project permissions do not make their URLs private.

## Tool names and source contract

Project and tool identifiers accept only lowercase ASCII letters, digits, underscores and hyphens. Project names have a maximum length of 100 characters; tool names have a maximum length of 197 and exclude `.py`. Names are validated as supplied: uppercase, whitespace and extensions are rejected with HTTP 422 rather than rewritten. Display titles may use other languages.

Publishing requires Python source with a top-level `main()`. `POST /api/tools/{project}/{name}/publish` requires a JSON body containing `{"content": "..."}`. Missing bodies, missing content and empty strings return HTTP 422; syntax and entry-point errors return HTTP 400. The CLI uploads `tools/{project}/{name}.py` by default, or reads `--file` / `--stdin`. The server never infers publication content from an existing database version or runtime cache.

MySQL stores published source and versions; local `tools/` files are recoverable runtime caches. Restore historical source through version rollback in the admin UI, which creates a new version. Tool details have no revision field and CLI `get --output` writes only the source file. Optimistic concurrency protection is not provided.
