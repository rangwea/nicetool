# NiceTool Codex Plugin

This plugin packages the repository's NiceTool skill for installation through a Codex plugin marketplace.

## Install from a clone

```bash
codex plugin marketplace add /absolute/path/to/nicetool
codex plugin add nicetool@personal
```

Start a new Codex task after installation so the `nicetool` skill is loaded.

## Install from Git

After this repository is pushed to a Git remote, replace `OWNER/REPOSITORY` with its GitHub location:

```bash
codex plugin marketplace add OWNER/REPOSITORY --ref main
codex plugin add nicetool@personal
```

## Update

Refresh the configured marketplace, reinstall the plugin, and start a new task:

```bash
codex plugin marketplace upgrade personal
codex plugin add nicetool@personal
```

The plugin does not contain NiceTool access tokens or local environment configuration. Each user must initialize their own NiceTool CLI environment and set its referenced token environment variable.
