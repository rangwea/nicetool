# Tool Development

A NiceTool tool is a Python file with a top-level `main()` function. The function renders the UI and handles user interaction.

## Minimal tool

```python
from nicegui import ui


def main():
    ui.label("Hello from NiceTool")
```

## Metadata

Tool files may include metadata in the module docstring:

```python
"""name: Order query
description: Search orders and export filtered results
tags: demo,query,export
"""
```

## Guidelines

- Keep one tool focused on one business task.
- Validate user input before querying or computing.
- Use platform data sources and variables for environment-specific values.
- Keep logs useful for preview and troubleshooting.
- Prefer read-only behavior unless the workflow is explicitly designed to write data.

## Tool names and source contract

Project and tool identifiers accept only lowercase ASCII letters, digits, underscores and hyphens. Project names have a maximum length of 100 characters; tool names have a maximum length of 197 and exclude `.py`. Names are validated as supplied: uppercase, whitespace and extensions are rejected with HTTP 422 rather than rewritten. Display titles may use other languages.

Publishing requires Python source with a top-level `main()`. `POST /api/tools/{project}/{name}/publish` requires a JSON body containing `{"content": "..."}`. Missing bodies, missing content and empty strings return HTTP 422; syntax and entry-point errors return HTTP 400. The CLI uploads `tools/{project}/{name}.py` by default, or reads `--file` / `--stdin`. The server never infers publication content from an existing database version or runtime cache.

MySQL stores published source and versions; local `tools/` files are recoverable runtime caches. Restore historical source through version rollback in the admin UI, which creates a new version. Tool details have no revision field and CLI `get --output` writes only the source file. Optimistic concurrency protection is not provided.
