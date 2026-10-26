# Development and Contributing

NiceTool uses Python 3.13+, uv, NiceGUI, FastAPI, SQLModel, MySQL, and ruff.

## Setup

```bash
uv sync
```

## Run

```bash
uv run main.py
```

## Checks

```bash
ruff check
ruff format
uv run python -m unittest discover -s tests
```

## Contribution guidelines

- Keep UI changes consistent with the existing theme and layout.
- Use `session_scope()` for database operations.
- Add or update tests when behavior changes.
- Avoid committing local `.env` files or secrets.
- Keep generated website docs in sync by running `uv run python scripts/build_website_docs.py` after documentation changes.
