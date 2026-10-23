# NiceGUI 3.15 Data Display and Charts

## Scope and Sources

Load for tables, pagination, row actions, trees, JSON, or visualization.
Baseline: NiceGUI 3.15.x. Sources: [official documentation](https://nicegui.io/documentation)
and [official 3.15 LLM reference](https://github.com/zauberzeug/nicegui/blob/v3.15.0/nicegui/llms.md).

For read-only statistics, dashboards, analytical computation, charts, or Excel
export, keep the implementation read-only and apply the standard NiceTool lifecycle.

## Tables and Pagination

Use `ui.table` for ordinary bounded results and source-side paging for large data:

```python
columns = [
    {"name": "id", "label": "ID", "field": "id", "align": "left"},
    {"name": "name", "label": "名称", "field": "name", "sortable": True},
]
table = (
    ui.table(columns=columns, rows=[], row_key="id")
    .props("flat dense")
    .classes("w-full")
)

table.rows = rows
table.update()
```

- Query total count and the requested page in the business layer.
- Reset to page 1 when filters or page size change.
- Clamp the current page after a smaller result set arrives.
- For zero results show `0 条`; never show the misleading range `1–0`.
- Disable unavailable previous/next actions.
- Put compact row actions in named slots and emit the complete row.
- Render untrusted cell content as text; do not interpolate it into HTML.

Use `ui.aggrid` only when advanced grid behavior is essential.

## Charts

For a small supporting chart, `ui.echart` is the default. Keep options declarative,
labels readable, and semantic colors consistent with the platform. Update an
existing chart rather than recreating it. Do not use a chart when a number, compact
table, or status label communicates the result more clearly.

## Failure Modes

- Loading every row and relying on client pagination.
- Recreating the table after every query.
- Page index remains out of range after filters reduce results.
- Row buttons use decorative icons without accessible meaning.
- A chart is decorative or duplicates the table without a question.

## Checklist

- Is data bounded and paged at the source?
- Are zero, loading, failure, and populated states explicit?
- Are page/range labels mathematically correct?
- Do row keys remain stable?
- Is the analytical workflow read-only and bounded?
