# NiceGUI 3.15 Foundations

## Scope and Sources

Load for NiceGUI architecture, page lifecycle, element placement, or routing.
Baseline: NiceGUI 3.15.x. Sources: [official documentation](https://nicegui.io/documentation),
[documentation index](https://nicegui.io/documentation/section_configuration_deployment#documentation_index),
[official 3.15 LLM reference](https://github.com/zauberzeug/nicegui/blob/v3.15.0/nicegui/llms.md),
and [v3.15.0 release](https://github.com/zauberzeug/nicegui/releases/tag/v3.15.0).
NiceTool project rules override generic NiceGUI examples.

## Production Rules

- Build with Python APIs first: `ui.*`, element methods, bindings, and refreshables.
- NiceGUI uses one shared asyncio event loop. A blocking handler can freeze every user.
- Module-level mutable objects are shared by all users. Keep tool state in the object
  created inside `main`, local page scope, or correctly scoped storage.
- `@ui.page` runs once per page load; it does not rerun when state changes.
- Context managers determine element parents through the current slot stack.
- Mutating an existing element preserves client state. Rebuild only a small,
  structural subtree with `@ui.refreshable` or `@ui.refreshable_method`.
- Render a skeleton first and load slow data asynchronously; page builders have a
  short response timeout.

## NiceTool Entrypoint

NiceTool owns routing and the page shell. A tool exposes an undecorated top-level
`main` and must not add another `@ui.page`:

```python
def main() -> None:
    with ui.column().classes("w-full gap-3"):
        ui.label("工具内容")


if __name__ in {"__main__", "__mp_main__"}:
    main()
    ui.run(title="工具标题", port=8080, show=True)
```

The run guard is for local execution. The platform imports and calls `main`.

## Choose the Smallest Mechanism

- Text/value/visibility change: mutate the element or use binding.
- A section changes structure: refresh that section.
- State must survive reload: use scoped storage only if the host supports it.
- A new route is needed in an ordinary app: use `@ui.page`; do not do this in a tool.

## Failure Modes

- Mutable module globals leak one user's filters or results to another.
- Recreating an entire table/page loses focus and scroll state.
- Direct DOM mutation diverges from NiceGUI's Python model.
- Database work during page construction hits the response timeout.
- A tool route conflicts with the platform-owned route.

## Checklist

- Is `main` top-level and undecorated?
- Is per-user mutable state owned by the current tool instance?
- Are elements created inside the intended parent context?
- Are updates in-place unless structure genuinely changes?
- Does the UI render before slow work begins?
