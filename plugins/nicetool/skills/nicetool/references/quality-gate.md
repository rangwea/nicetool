# Nicetool Quality Gate

## Metadata

Use a module docstring with nonempty `project`, `name`, `description`, `creator`,
`created_at`, `updated_at`, and `tags`. Use 2–5 comma-separated purpose tags.
Replace template identity and dates with the real tool's values.

## Entrypoint

- `main` must be a top-level function.
- The platform calls `main()` without arguments (and awaits async functions).
  Do not require arguments or make the entrypoint a generator; nested helper
  generators are allowed.
- Do not decorate or dynamically generate `main`.
- Keep the local run guard:

```python
if __name__ in {"__main__", "__mp_main__"}:
    main()
    ui.run(title="[工具标题]", port=8080, show=True)
```

## UI Rules

Keep tools single-file and reuse the platform shell/theme. Use the compact defaults
in `design.md` when changing UI; preserve existing layout for logic-only edits.

## Runtime Robustness

- Wrap data access and user-triggered operations with friendly `ui.notify` errors.
- Use pagination for large datasets.
- Move blocking I/O to `run.io_bound` and CPU-heavy work to `run.cpu_bound`.
- Keep mutable filters, rows, selections, and busy state private to the tool instance.
- Implement initial/loading, empty, success, and failure states where applicable.
- Log technical exceptions; never expose raw exception text to users.
- Read platform variables through `core.variable_manager.variables`; validate string
  conversions and never log variable values.
- MySQL uses `db.get_mysql_session`; MongoDB uses `db[name]` from
  `core.datasource_manager`. Only managed enums use `core.uix.enums_select`.
- Complex tools may use classes for business state, but `main` remains a top-level function.

## Static Validation and Delivery

Run the validator from `SKILL.md` after edits. Fix reported errors before handoff.
It never imports the tool; a missing compatible interpreter means unverified, not passed.

Before preview, check private state, parameterized queries, bounded pagination,
submitted-filter snapshots, control recovery, and missing configuration handling.
Keep blocking operations off the event loop. Report only checks actually performed.
