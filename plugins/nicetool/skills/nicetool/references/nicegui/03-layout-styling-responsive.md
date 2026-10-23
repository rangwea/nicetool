# NiceGUI 3.15 Layout, Styling, and Responsive UI

## Scope and Sources

Load for cards, rows, grids, responsive forms, or custom styling.
Baseline: NiceGUI 3.15.x. Sources: [official documentation](https://nicegui.io/documentation)
and [official 3.15 LLM reference](https://github.com/zauberzeug/nicegui/blob/v3.15.0/nicegui/llms.md).
Also apply `../design.md`, which is authoritative for NiceTool visual decisions.

## Styling Order

1. NiceGUI Python parameter or element property.
2. Tailwind/Quasar utility through `.classes()`.
3. Quasar component option through `.props()`.
4. Narrow, locally namespaced CSS only when necessary.
5. JavaScript only for capability unavailable in Python.

Avoid broad inline `.style()`, raw hex colors, global selectors, and DOM
manipulation for normal layout and appearance.

## NiceTool Layout Baseline

The platform supplies the page shell:

```python
with ui.column().classes("w-full gap-3"):
    with ui.card().classes("w-full").props("flat"):
        with ui.row().classes("w-full gap-2 items-end flex-wrap"):
            ui.input("关键词").props("outlined dense color=primary").classes(
                "min-w-[12rem] flex-1"
            )
```

- Do not add outer `max-w-*`, `mx-auto`, broad page padding, header, or drawer.
- Use rows for actions/short fields, columns for semantic sections, and grids for
  genuinely scannable equal columns.
- Allow filter rows to wrap; fields get minimum width and flexible growth.
- Use responsive classes such as `grid-cols-1 md:grid-cols-2`.
- Keep one primary action. Secondary actions use flat or outline treatment.
- Buttons are text-only and dense by default; compact table-row actions are the
  documented icon exception.

## Responsive Decisions

- Design narrow screens first: one column, wrapped actions, no fixed page width.
- Do not hide required data; shorten, prioritize, wrap, or disclose details.
- Wide tables may scroll, but filters and pagination must remain usable.
- Dense layouts still need usable touch targets and visible focus.

## Failure Modes

- Rebuilding the platform shell inside the tool.
- Decorative gradients, shadows, or colored cards compete with data.
- Fixed widths overflow on narrow screens.
- Unscoped `ui.add_css` affects every tool in the process.
- Raw JS is used where a Python API or class exists.

## Checklist

- Does the root use `w-full gap-3` and rely on the host shell?
- Is the page readable at narrow and wide widths?
- Are theme and semantic roles used instead of hardcoded colors?
- Is CSS local, minimal, and necessary?
- Is there exactly one visually dominant action or result?
