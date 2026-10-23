# NiceGUI 3.15 Inputs, Events, and Validation

## Scope and Sources

Load for forms, filters, uploads, keyboard events, validation, or enum selection.
Baseline: NiceGUI 3.15.x. Sources: [official documentation](https://nicegui.io/documentation)
and [official 3.15 LLM reference](https://github.com/zauberzeug/nicegui/blob/v3.15.0/nicegui/llms.md).

## Selection Rules

- Text: `ui.input`; long text: `ui.textarea`; numeric constraints: `ui.number`.
- Small fixed choices: `ui.select`, `ui.radio`, or `ui.toggle`.
- Boolean: `ui.checkbox` or `ui.switch`.
- Dates/times: `ui.date_input` and `ui.time_input` when typing is useful.
- Managed business enums: use `core.uix.enums_select`; never hardcode options.
- Tool-local options that are not centrally managed: use standard NiceGUI controls.

Use `outlined dense color=primary` on ordinary inputs. Prefer labels when meaning
would otherwise disappear after a value is entered.

## Events

Prefer constructor callbacks and typed event values:

```python
from nicegui.events import ValueChangeEventArguments


def change_keyword(event: ValueChangeEventArguments) -> None:
    state.keyword = event.value or ""


ui.input("关键词", on_change=change_keyword)
ui.button("查询", on_click=run_query)
```

- Use `.on()` only when no Python constructor callback exists.
- Read `.value`, `.previous_value`, `.sender`, and `.client`; avoid undocumented
  `e.args` shapes when a typed event exists.
- Throttle high-frequency events.
- Async event handlers are supported and should own non-blocking workflows.
- Disable the primary button during submission to prevent duplicates.

## Validation

Use component validation for immediate feedback and validate the complete business
rule again in the submit handler:

```python
email = ui.input(
    "邮箱",
    validation={"请输入有效邮箱": lambda value: "@" in (value or "")},
).props("outlined dense color=primary")
```

Normalize values before the business layer. Treat browser values as untrusted and
enforce authorization and data constraints server-side.

## Failure Modes

- A placeholder is the only label for an ambiguous field.
- A managed enum is copied into a hardcoded `options` list.
- Every keystroke queries the backend without throttle or explicit submit.
- A sync handler performs blocking I/O.
- UI validation is assumed to protect the data layer.
- Raw exception messages are shown to the user.

## Checklist

- Does each control match the data type and frequency of use?
- Are managed enums loaded through `enums_select` only?
- Are event values read from stable typed attributes?
- Are validation, normalization, duplicate prevention, and friendly failure
  feedback present?
