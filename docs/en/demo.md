# Demo: What AI Can Create for You

The demo environment is designed to reduce first-use friction for open-source users. It shows what NiceTool can do before users study deployment details.

## What is included

- A one-command demo startup script.
- Demo data for order and sales scenarios.
- Three finished tools: order query, quote calculator, and sales dashboard.
- English UI examples that demonstrate filters, forms, cards, charts, and tables.
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
