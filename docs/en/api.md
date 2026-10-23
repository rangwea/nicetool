# API Navigation

NiceTool exposes FastAPI routes for tools, data sources, previews, initialization, and client integration.

## API documentation

When the server is running, open:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Common route groups

| Group | Purpose |
| --- | --- |
| `/api/tools` | Tool management, preview, publish, and version operations. |
| `/api/datasources` | Data source CRUD. |
| `/client/tool/{token}` | Temporary preview client route. |
| `/api/init.sh` | CLI environment initialization script. |

Use the interactive API pages for exact request and response schemas.

## Tool names and source contract

Project and tool identifiers accept only lowercase ASCII letters, digits, underscores and hyphens. Project names have a maximum length of 100 characters; tool names have a maximum length of 197 and exclude `.py`. Names are validated as supplied: uppercase, whitespace and extensions are rejected with HTTP 422 rather than rewritten. Display titles may use other languages.

Publishing requires Python source with a top-level `main()`. `POST /api/tools/{project}/{name}/publish` requires a JSON body containing `{"content": "..."}`. Missing bodies, missing content and empty strings return HTTP 422; syntax and entry-point errors return HTTP 400. The CLI uploads `tools/{project}/{name}.py` by default, or reads `--file` / `--stdin`. The server never infers publication content from an existing database version or runtime cache.

MySQL stores published source and versions; local `tools/` files are recoverable runtime caches. Restore historical source through version rollback in the admin UI, which creates a new version. Tool details have no revision field and CLI `get --output` writes only the source file. Optimistic concurrency protection is not provided.
