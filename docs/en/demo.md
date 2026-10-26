# Demo: What AI Can Create for You

The demo environment is designed to reduce first-use friction for open-source users. It shows what NiceTool can do before users study deployment details.

## What is included

- A one-command demo startup script.
- Demo data for order and sales scenarios.
- Three finished tools: order query, quote calculator, and sales dashboard.
- Examples that demonstrate filters, forms, cards, charts and tables; platform language follows `LANGUAGE` in `.env` (or `.env.example` when absent).
- Seed logic that updates demo tools when their source files change.

## Start the demo

```bash
sh scripts/demo.sh
```

The script starts the application and a MySQL container, initializes demo data, and makes the platform available at `http://127.0.0.1:8000`.

## Demo tools

| Tool | What it demonstrates |
| --- | --- |
| Order query | Search, filters, pagination, status badges, and export-oriented results. |
| Quote calculator | Form input, validation, computed output, and summary cards. |
| Sales dashboard | KPI cards, charts, customer ranking, and read-only analytics. |

## Why this matters

The goal is to let users first experience “AI helped me create a usable business tool,” then learn how to deploy, secure, and extend the platform.

## Restart and reset

Restarting preserves the database volume, but seeding writes a new version when a preset tool differs from its bundled source. It can overwrite edits to the three preset tools. Save custom work under new tool names. Unchanged source is skipped; deleted preset tools are recreated. Existing client environments are retained.

Stop while preserving data:

```bash
docker compose --env-file /dev/null -f compose.demo.yaml down
```

To delete all demo data and changes, explicitly reset the volumes:

```bash
docker compose --env-file /dev/null -f compose.demo.yaml down --volumes
sh scripts/demo.sh
```

The demo disables authentication and uses an isolated database. Its example tools depend on `examples.demo.data`; create tutorial tools inside this repository. Preview first, then publish only after verification. For troubleshooting, run `python3 scripts/doctor.py --server http://localhost:8000`; HTTP health alone does not verify the database or tool behavior.
