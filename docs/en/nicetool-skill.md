# CLI and Skill

The NiceTool Skill helps an AI coding agent create, preview, publish, delete, and inspect tools through the NiceTool CLI.

NiceTool tools are single-file Python modules with a top-level `main()` function. Users do not need to think about Python; the platform uses it as the runtime for AI-generated business tools.

## Install the Skill

Copy the Skill package into the agent's Skill search directory. Keep scripts and references together; do not copy only `SKILL.md`.

```bash
cp -R plugins/nicetool/skills/nicetool .agents/skills/nicetool
```

## Connect an instance

Use the repository CLI directly:

```bash
export NICETOOL_TOKEN='replace-with-your-token'
uv run python plugins/nicetool/skills/nicetool/scripts/tool-cli.py --server http://localhost:8000 list
```

After installation into a target project, use `.agents/skills/nicetool/scripts/tool-cli.py` as the script path.

For multiple instances, initialize configuration through `/api/init.sh`, then select an environment with `--env <name>` or provide a TOML file with `--config <path>`. Environment name, URL, and `token_env` come from the admin environment page.

## Typical workflow

1. Ask the AI agent to create or modify a tool.
2. The agent writes a NiceTool-compatible tool file.
3. Preview the tool in NiceTool and inspect logs.
4. Publish the approved version.
5. Use version history to roll back or audit changes.

## Recommended tool shape

A tool should be compact, focused, and safe by default. Read-only query and analytics tools should not mutate business data. Configuration should come from NiceTool variables, data sources, and enums instead of hard-coded values.
