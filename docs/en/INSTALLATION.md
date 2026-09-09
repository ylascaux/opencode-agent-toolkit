# Installation

`just` is the primary command surface.

## macOS quick start

```bash
brew install just
git clone https://github.com/ylascaux/opencode-agent-toolkit.git
cd opencode-agent-toolkit
just install
just models
just doctor
```

`just install` creates `.env` only when absent, creates `.venv`, installs scanner/API dependencies, generates both OpenCode configs, validates them, runs the Python tests and validates model-tier resolution. For complete validation, including the Node runtime tests, use `just check`.

It does **not** install global packages, use `sudo`, edit shell startup files or modify `~/.config`.

## Default model profile

The default work profile is GitHub Copilot:

```text
LOW    -> github-copilot/gpt-5.6-luna
MEDIUM -> github-copilot/gpt-5.6-terra
HIGH   -> github-copilot/gpt-5.6-sol
```

Check the models exposed to your account with:

```bash
opencode models github-copilot
```

If your account exposes different IDs, edit `profiles/copilot.env.example` and reapply it:

```bash
just profile copilot
```

## Switch providers / personal profile

```bash
just profiles
just profile copilot
just profile codex
just models
```

Profile switching changes only `MODEL_PROFILE`, `MODEL_LOW`, `MODEL_MEDIUM` and `MODEL_HIGH` in `.env`.

Persistent per-agent overrides belong in `.env.local`, which profile switching never modifies:

```bash
MODEL_BUILDER=openai/gpt-5.3-codex
MODEL_REVIEWER=github-copilot/gpt-5.6-sol
```

## Optional user command: run from anywhere

```bash
just install-user
```

This creates only:

```text
~/.local/bin/oc -> <toolkit>/scripts/opencode-agents
```

The launcher preserves the current directory:

```bash
cd ~/Projects/my-api
oc
```

OpenCode uses `~/Projects/my-api` as the workspace while loading the toolkit configuration and model mappings from the toolkit repository.

Check/remove the link safely:

```bash
just user-status
just uninstall-user
```

The installer never overwrites unrelated files or symlinks and never edits your shell. If `oc` is already used, choose another name:

```bash
just install-user opencode-agents
```

## Runtime selection

`.env` supports `OPENCODE_MAJOR=1`, `2`, or `auto`. One-off selection is available through `just v1` and `just v2`.

## Optional LiteLLM discovery

LiteLLM is not required for normal usage. Future gateway-based discovery remains available through:

```bash
just configure-litellm
```


## Daily recipes

```bash
just install
just profile copilot
just profiles
just models
just install-user
just user-status
just uninstall-user
just doctor
just run
just check
just test
just scan
just api
just refresh
just clean
```
