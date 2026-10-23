# NiceTool CLI Environments

Use named environments when more than one NiceTool instance is available.
Environment selection applies to remote commands; `create` remains local-only.

## Configuration

The default configuration path is
`$XDG_CONFIG_HOME/nicetool/config.toml`, falling back to
`~/.config/nicetool/config.toml`.

```toml
default_environment = "test"

[environments.test]
url = "https://nicetool.test.example.com"
token_env = "NICETOOL_TEST_TOKEN"

[environments.prod]
url = "https://nicetool.example.com"
token_env = "NICETOOL_PROD_TOKEN"
production = true
```

Keep Token values outside the TOML file. The installer stores browser-authorized
tokens in `${XDG_CONFIG_HOME:-~/.config}/nicetool/credentials.env` with mode
`0600`, and the CLI reads that file automatically. Explicit process environment
variables still take precedence:

按 `SKILL.md` 将 `NICETOOL_SKILL_ROOT` 设为实际 skill 绝对路径，保持当前工作目录。

```bash
export NICETOOL_TEST_TOKEN="..."
export NICETOOL_PROD_TOKEN="..."
```

Use `--config` or `NICETOOL_CONFIG` for a custom configuration path. Use
`--env` or `NICETOOL_ENV` to select an environment.

## Commands

```bash
python "$NICETOOL_SKILL_ROOT/scripts/tool-cli.py" \
  --env test preview demo chart --file tools/demo/chart.py

python "$NICETOOL_SKILL_ROOT/scripts/tool-cli.py" \
  --env test publish demo chart

python "$NICETOOL_SKILL_ROOT/scripts/tool-cli.py" \
  --env prod publish demo chart --yes
```

`--server` and `--token` are one-command overrides. A direct `--server`
without `--env` is treated as a custom target and does not inherit the default
environment.

## Production Safety

An environment is production only when it declares `production = true`.
Production `publish` and `delete` require interactive confirmation or an
explicit `--yes` in JSON, CI, and other non-interactive runs. An Agent may use
`--yes` only after the user explicitly authorizes the production action and
target.

Never print Token values in command output, JSON, logs, or errors.

## Bootstrap from NiceTool

When the user provides and confirms a trusted NiceTool URL, its public bootstrap
script can create the same configuration without requiring the CLI:

```bash
curl -fsSL https://nicetool.example.com/api/init.sh | sh
```

Reuse a trusted service URL already supplied in the conversation; otherwise ask for
it. Do not infer the service from a preview URL. Initialization runs independently
of this skill, the CLI, Node.js or npx. Never request or display Token values, or
write them into project files or TOML; the browser authorization saves credentials.

The script writes atomically with mode `0600`, follows the XDG configuration path,
and refuses to overwrite an existing file. Use either option only when requested:

```bash
curl -fsSL https://nicetool.example.com/api/init.sh | sh -s -- \
  --config /custom/path/config.toml

curl -fsSL https://nicetool.example.com/api/init.sh | sh -s -- --force
```

The downloaded script embeds environment URLs, production flags, and Token
environment-variable names. It must never embed Token values. During installation
it opens the browser for a short-lived device authorization and persists the
returned credential outside the project. `--skip-auth` is reserved for CI or
Skill-only updates.

A custom `--config` path does not require changing global environment variables.
