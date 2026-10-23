# NiceGUI 3.15 Async Tasks and Multi-user Safety

## Scope and Sources

Load for database/API/file work, CPU computation, background loading, progress,
timers, or concurrency.
Baseline: NiceGUI 3.15.x. Sources: [official documentation](https://nicegui.io/documentation)
and [official 3.15 LLM reference](https://github.com/zauberzeug/nicegui/blob/v3.15.0/nicegui/llms.md).

## Execution Choice

| Work | Use |
| --- | --- |
| Native async library | `await` it directly |
| Blocking database/API/file I/O | `await run.io_bound(function, *args)` |
| CPU-heavy, picklable function | `await run.cpu_bound(function, *args)` |
| Fire-and-forget coroutine | `background_tasks.create(coroutine)` |
| Repeated callback | `ui.timer` |

```python
from nicegui import run


def blocking_query(keyword: str) -> list[dict[str, object]]:
    return repository.search(keyword)  # BUSINESS REPLACEMENT POINT


async def search() -> None:
    rows = await run.io_bound(blocking_query, keyword_input.value or "")
```

`run.cpu_bound` functions must be module-level and arguments/results picklable.
Prefer NiceGUI runners to hand-built executors.

## User Experience Contract

- Render the page before slow work starts.
- Set busy state and disable duplicate actions before awaiting.
- Always restore controls in `finally`.
- Represent loading, success/empty, and failure independently.
- Log technical exceptions; display a stable, friendly message.
- Show a percentage only when total work is known. Otherwise use an indeterminate
  spinner or ongoing notification.

## Multi-user Rules

- Never store rows, filters, busy flags, or selected records in module globals.
- A tool instance created in `main` is the normal per-page state owner.
- Shared caches require explicit concurrency design and cannot hold user-specific
  authorization results.
- Tenant and row permissions belong in the business/data layer.
- Reject overlapping requests or use a generation token to ignore stale results.

## Failure Modes

- `time.sleep`, `requests`, or a synchronous DB driver runs in an async handler.
- Bare `asyncio.create_task` bypasses NiceGUI task management.
- A button remains disabled after an exception.
- Background work updates another client's elements.
- A fake progress bar advances without measurable completed work.

## Checklist

- Is every blocking operation off the shared event loop?
- Is state private to the current tool/client?
- Are controls restored on all paths?
- Can stale responses or duplicate submissions occur?
- Is progress determinate only when total work is known?
