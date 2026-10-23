# NiceGUI 3.15 Security, Testing, and Interop

## Scope and Sources

Load for HTML/JavaScript, authentication-sensitive UI, FastAPI integration, custom
routes, testing, or deployment behavior.
Baseline: NiceGUI 3.15.x. Sources: [official documentation](https://nicegui.io/documentation),
[official 3.15 LLM reference](https://github.com/zauberzeug/nicegui/blob/v3.15.0/nicegui/llms.md),
and [v3.15.0 release](https://github.com/zauberzeug/nicegui/releases/tag/v3.15.0).

## Security Boundaries

- UI visibility is not authorization. Enforce identity, tenant, row, and action
  permissions in the service/data layer.
- Prefer text elements. Escape/sanitize untrusted content before `ui.html`, table
  slots, Markdown extensions, or JavaScript interpolation.
- Do not expose secrets, tokens, SQL, or personal data through props, event payloads,
  logs, notifications, URLs, or filenames.
- Validate uploads, query inputs, sort fields, identifiers, and pagination bounds.
- Use parameterized database APIs; never concatenate user input into SQL.
- NiceTool mutations must match the user's request; preview is not permission to
  publish or change business data.

## Interop Rules

- Use Python APIs first. JavaScript is a last resort for browser-only information or
  a component capability NiceGUI does not expose.
- Do not change ordinary content/styling through the DOM; Python updates overwrite it.
- The host owns FastAPI routes, middleware, storage secret, mount path, and startup.
  A tool must not call `ui.run_with`, add middleware, or register a competing page.
- The local run guard may call `ui.run`; imported platform execution does not.

## Testing Guidance

- Mark stable elements with `.mark("semantic-name")` for reliable selectors.
- Prefer NiceGUI's `User` fixture for fast Python-side interaction tests.
- Use `Screen` only for JavaScript, rendering, responsive layout, or charts.
- Test transitions: validation, busy state, empty result, exception recovery,
  pagination reset, and authorization failure.
- Preview is the platform integration check; use `prelog` when it fails or the user
  reports a runtime problem.

## Failure Modes

- Hidden buttons are treated as access control.
- User data is interpolated into raw HTML or JavaScript.
- A tool registers global middleware/routes in the shared host.
- Tests depend on generated DOM classes or timing sleeps.
- Preview success is treated as permission to publish.

## Checklist

- Are authorization and input constraints enforced below the UI?
- Is all untrusted content rendered safely?
- Does the tool respect the platform-owned lifecycle?
- Are test selectors semantic and stable?
- Do tests cover failure recovery and state transitions?
