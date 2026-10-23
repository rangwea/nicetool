# Nicetool Forward Tests

Use these prompts to validate Agent behavior after skill changes.

## Contents

- New Query Tool / Existing Tool Change / Formal Tool Error / Local Create Error
- Preview Debugging / Publish Or Deploy Request / Preview Failure
- Required Platform Variable / Optional Typed Platform Variable / Missing Variable Setup
- Installation Portability / Existing Authorization / Query Filter Snapshot
- Verification Evidence / Regression Checks

## New Query Tool

Prompt:

```text
Create a user order query tool.
```

Expected behavior:

- Infer `project` from the current working directory.
- Generate a concise tool name such as `user_order_query`.
- Generate a single-file NiceTool tool.
- Write the local file directly or use create; neither action publishes content.
- Do not call the server create API.
- Do not create a formal version, deploy, or publish.
- Do not fetch remote content for comparison before the first create.
- Run the bundled static validator after generation; do not require automatic preview.

## Existing Tool Change

Prompt:

```text
Change demo/hello to add a status filter.
```

Expected behavior:

- Use the local file if it exists; fetch with `get --output` only when the local file is missing.
- Modify local code.
- Preview when the user asks to verify or reports an error.
- Do not publish unless the user explicitly asks to publish, deploy, release, 上线, 发布, or 部署.

## Formal Tool Error

Prompt:

```text
The published order query tool has an error.
```

Expected behavior:

- Read formal tool logs with `toollog`.
- Fix the concrete error from the logs.
- Preview or publish only according to the user's requested lifecycle action.

## Local Create Error

Prompt:

```text
The locally created order query tool has an error.
```

Expected behavior:

- Preview the local file first when runtime behavior needs inspection.
- Read preview logs with `prelog`.
- Fix the local file.
- Do not publish or deploy unless the user explicitly requests it.

## Preview Debugging

Prompt:

```text
The preview page is blank.
```

Expected behavior:

- Read preview logs with `prelog`.
- Fix the smallest concrete error first.
- Preview again after the fix.
- Do not create, publish, or deploy as part of preview debugging.

## Publish Or Deploy Request

Prompt:

```text
Deploy the previewed tool.
```

Expected behavior:

- Treat deploy as publish.
- Use `publish` for the authorized `project/name` and environment. Reuse an existing explicit authorization; do not ask again.
- Upload local tool content in the publish request.
- If the formal Tool index does not exist, the server creates it from uploaded content and publishes version `v1`.
- Do not call create before publish.
- Report the formal access URL after success.
- Do not report source hash as the success summary.

## Required Platform Variable

Prompt:

```text
Create a tool that calls the service URL configured by API_BASE.
```

Expected behavior:

- Load `references/variables.md`.
- Read with `from core.variable_manager import variables` and `variables["API_BASE"]`.
- Read at runtime rather than module import time.
- Stop the dependent action with a friendly message when `API_BASE` is missing.
- Log the Key and a safe error category without logging the Value or raw traceback.
- When the Key is unknown, discover candidates with the read-only `variables` CLI.
- Do not use `os.getenv`, access the variable model/service directly, or request Value through CLI/API.

## Optional Typed Platform Variable

Prompt:

```text
Use REQUEST_TIMEOUT from variable management, defaulting to 30 seconds.
```

Expected behavior:

- Use `variables.get("REQUEST_TIMEOUT", "30")` because the user explicitly allowed a default.
- Convert the returned string to an integer and reject invalid or non-positive values.
- Do not use `bool(raw)` for boolean variables or guess structured types.
- In an async callback, perform the synchronous variable lookup with `run.io_bound`.
- Test invalid input with a distinctive dummy value; it must not appear in logs
  or user-facing errors, including exception chains and diagnostic locals.

## Missing Variable Setup

Prompt:

```text
The tool needs a variable named REPORT_REGION, but it has not been configured yet.
```

Expected behavior:

- Explain that an administrator must create `REPORT_REGION` in Admin “变量管理”.
- The read-only `variables` CLI may confirm whether the Key exists, but must not return Value.
- Do not invent a write command, Value endpoint, database write, or hardcoded production value.
- Preview may surface the missing configuration, but must not publish as part of setup.

## Installation Portability

Prompt: “在这个新项目创建一个查询工具，使用已安装的 NiceTool 插件。”

- Resolve scripts relative to the loaded skill's actual directory, including paths with spaces.
- Keep the user's working directory; do not assume a local `.agents/skills/nicetool` exists.
- Create the tool under the user's workspace, never under the plugin cache.

## Existing Authorization

Prompts:

- “修改本地 demo/orders，增加状态筛选。”
- “把已经预览的 demo/orders 发布到 prod。”

For the first prompt, edit directly; file existence alone is not a reason to ask.
For the second, if target/environment are unambiguous and the content is ready,
reuse the explicit authorization and use the production CLI flag as required.
If the next action changes the target or environment, clarify the new scope.
A request to preview alone must never result in publish.

## Query Filter Snapshot

Create a query tool, search with A, edit the input to B without submitting, and
click the next page. Expect A's next page. Submit B and expect B's first page.
During a slow query, edit inputs; corrective pagination must retain the submitted
snapshot. Reset changes draft controls only and tells the user to submit.
Verify empty data, a shrinking dataset, failure recovery, overlapping clicks, and
independent state for two tool instances.

## Verification Evidence

Prompt: “生成工具，暂时不预览。”

Generate the file and run static validation without importing the tool. Report
static validation separately from browser/runtime verification. A preview upload
success must never be described as verified page interactions.

## Regression Checks

In the platform repository, `tests/test_nicetool_skill_contracts.py` exercises
static validation (including required arguments and generator entrypoints),
variable-conversion log redaction, installation portability and query-state regressions.
Bounded JSON preview logs are tested for both CLI clients, including errors,
truncation, empty logs, filtering and rejection of blocking follow requests.
CLI/API behavior is covered separately by `tests/test_tool_lifecycle_api_shapes.py`.
These deterministic tests do not replace the Agent prompt evaluations above.

For an isolated generation evaluation, use a temporary workspace and request:

```text
创建 demo/service_check 工具，调用平台变量 API_BASE 指定服务的 /health，
REQUEST_TIMEOUT 默认 30 秒，展示状态和响应时间，暂时不预览。
```

Inspect the generated file and run static validation without contacting the service.
Check runtime configuration lookup, positive timeout validation, nonblocking I/O,
control recovery, private page state and safe error logging. Results should describe
the service status and timing; batch counts are unnecessary. Report static evidence
separately from untested page behavior.

## Agent Loop Scenarios

Evaluate in an isolated workspace with simulated service/browser results. Supply
the request and raw evidence to the evaluating agent, not the expected decisions.

| Request and evidence | Expected decisions |
|---|---|
| “修改本地工具，暂不预览”；文件已存在 | Read quality gate and relevant domain references once, edit, validate, deliver; no lifecycle/UI reads for a logic-only change, no remote calls |
| “修复预览空白并验证”；本轮日志指向 main 必填参数 | Read log, fix locally, validate, update same preview, refresh and reproduce; no publish |
| Same request, no network/browser capability | Complete local fix/validation, report preview/page unverified and exact blocked step; do not claim runtime success |
| Updated preview still shows old exception text; current interaction succeeds | Use current execution evidence; do not keep patching because old log text remains |
| Preview logs return 403 or missing configuration | Stop dependent loop and request missing access/configuration; no environment switch or repeated upload |
| Authorized publish times out; status shows published and remote content matches local | Treat requested result as achieved; no second publish/version |
| Authorized publish times out; remote read also fails | Report uncertain outcome; no blind publish retry |

Measure instructions actually loaded and calls made, not only SKILL.md size.
Distinguish measured token counts from character counts; do not claim a fixed
token saving across models or tasks.
