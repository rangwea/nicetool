# NiceGUI 3.15 State, Binding, and Refresh

## Scope and Sources

Load for dynamic UI, dependent controls, refreshable sections, or persistent state.
Baseline: NiceGUI 3.15.x. Sources: [official documentation](https://nicegui.io/documentation)
and [official 3.15 LLM reference](https://github.com/zauberzeug/nicegui/blob/v3.15.0/nicegui/llms.md).

## State Ownership

| Need | Preferred location |
| --- | --- |
| Current tool/page only | Local variables or an instance created in `main` |
| Current connection | `app.storage.client` |
| Current browser tab across reload | `app.storage.tab` |
| Current user across reload | `app.storage.user` |
| Deliberately shared by all users | `app.storage.general` |

`user` and `browser` storage require the host storage secret. Never use a
mutable module global for per-user filters, selections, or results.

## Update Decision

- Bind when continuous synchronization is useful.
- Use `set_text`, `set_value`, or `visible` for a property update.
- Assign complex data and call `.update()` when the component requires it.
- Use `@ui.refreshable` only when child structure changes.
- Use `@ui.refreshable_method` for a class-owned dynamic section.

```python
class Tool:
    def __init__(self) -> None:
        self.items: list[str] = []

    @ui.refreshable_method
    def render_items(self) -> None:
        if not self.items:
            ui.label("暂无数据").classes("text-sm text-gray-500")
            return
        for item in self.items:
            ui.label(item)
```

Bindings propagate changes; do not routinely call `.update()` after changing a
bound value. Prefer explicit submission for backend filters.

## Stable Async UI

Capture client-owned elements before awaiting and update the same elements when
work finishes. Guard overlapping requests with a busy flag or generation token.
Discard results from superseded requests.

## Failure Modes

- Module state leaks between users.
- A whole-page refresh destroys focus and scroll.
- Binding and manual mutation race on the same value.
- A stale async response overwrites a newer result.
- Storage scope/persistence was not deliberately selected.

## Checklist

- Is every mutable value owned at the correct scope?
- Can a property update replace a structural rebuild?
- Is refresh limited to the smallest coherent subtree?
- Are concurrent or out-of-order results handled?
- Are bound values free from redundant manual updates?
