# NiceGUI 3.15 Feedback, Dialogs, and Files

## Scope and Sources

Load for loading/empty/failure feedback, confirmations, detail dialogs, uploads,
downloads, clipboard, or media files.
Baseline: NiceGUI 3.15.x. Sources: [official documentation](https://nicegui.io/documentation)
and [official 3.15 LLM reference](https://github.com/zauberzeug/nicegui/blob/v3.15.0/nicegui/llms.md).

## State Feedback

Use persistent page state for information users must inspect and notifications for
brief acknowledgements:

- Initial: explain the next action only when the page cannot load directly.
- Loading: spinner/skeleton plus a short phrase; disable duplicate actions.
- Empty: say what was searched and offer clearing filters or another next step.
- Failure: preserve inputs, provide retry, and log technical detail.
- Success: show the result in-page; notify only for confirmation.

`ui.notification(..., spinner=True)` suits an ongoing action that later changes
message and type. Never expose exception strings, SQL, tracebacks, tokens, or
internal service addresses in notifications.

## Dialogs

- Use a dialog for focused details, confirmation, or a short secondary form.
- Destructive confirmation names the target and consequence.
- Provide a clear close/cancel path; do not put an entire page in a dialog.
- Prefer reusing one dialog for repeated row details when practical.

## Uploads and Downloads

- Configure file size/count/type limits and handle rejection.
- Treat names/content as untrusted; never build paths from uploaded names directly.
- Process large files off the event loop.
- Use approved temporary locations and define cleanup.
- Use `ui.download` or a server route; never embed secrets in URLs.
- NiceTool normally relies on platform routes rather than mounting new roots.

Excel export and analytical datasets must define explicit row limits and
determinate export progress requirements.

## Failure Modes

- A toast is the only place where a long result or error appears.
- Failure clears the user's filters or form.
- Dialogs are created repeatedly and retained unnecessarily.
- Uploaded filenames escape the intended directory.
- Large file reads/writes block the shared event loop.
- A percentage is shown without a measurable total.

## Checklist

- Are all four operational states visible and actionable?
- Are technical details logged rather than exposed?
- Do dialogs have a focused purpose and close path?
- Are file limits, path safety, async processing, and cleanup defined?
- Does the export have a bounded row limit and clear progress feedback?
