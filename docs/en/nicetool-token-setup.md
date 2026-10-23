# Token Setup

The NiceTool CLI uses a token to authenticate against a server instance.

## Environment variable

```bash
export NICETOOL_TOKEN='replace-with-your-token'
```

Use the token variable configured for the selected CLI environment. Token values are not distributed by the initialization script; only token variable names are shared.

## Multiple environments

Initialize CLI configuration from the server, then select an environment:

```bash
uv run python plugins/nicetool/skills/nicetool/scripts/tool-cli.py --env demo list
```

You can also provide a TOML file explicitly with `--config <path>`.
