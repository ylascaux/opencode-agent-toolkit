# Installation

`just` is the primary command surface.

## macOS quick start

Prerequisites: Bash, Python 3.11+, `just`, and the native runtime you plan to use: `opencode` for V1 or `opencode2` for V2. Install the runtime with its official procedure; the toolkit does not install it or migrate authentication.

```bash
brew install just
git clone https://github.com/ylascaux/opencode-agent-toolkit.git
cd opencode-agent-toolkit
just install
just doctor
```

`just install` creates `.env` only when absent, generates both native OpenCode configurations, and installs the `oc` and `oc2` launchers in `~/.local/bin`. Add that directory to `PATH` yourself if needed.

It does **not** install packages, use `sudo`, edit shell startup files, modify `~/.config`, contact a provider, or start a background server.

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
just profile copilot
just profile codex
```

Profile switching updates `MODEL_PROFILE`, `MODEL_LOW`, `MODEL_MEDIUM` and `MODEL_HIGH` in `.env`. It also removes legacy per-agent `MODEL_*` mappings from `.env` and saves them in `.env.model-overrides.backup`.

Persistent per-agent overrides belong in `.env.local`, which profile switching never modifies:

```bash
MODEL_BUILDER=openai/gpt-5.3-codex
MODEL_REVIEWER=github-copilot/gpt-5.6-sol
```

## Run from anywhere

`just install` installs these toolkit-owned links:

```text
~/.local/bin/oc -> <toolkit>/scripts/opencode-agents
~/.local/bin/oc2 -> <toolkit>/scripts/opencode-agents
```

The launcher preserves the current directory:

```bash
cd ~/Projects/my-api
oc
```

OpenCode uses `~/Projects/my-api` as the workspace while loading the toolkit configuration and model mappings from the toolkit repository.

Remove the toolkit-owned links safely:

```bash
just uninstall
```

The installer never overwrites unrelated files or symlinks and never edits your shell. `just uninstall` removes only the `oc` and `oc2` links owned by this toolkit.

## Runtime selection

Use `oc` for OpenCode V1 and `oc2` for OpenCode V2. Both preserve the current directory as the workspace. Set `OPENCODE_BIN` to use an explicit runtime binary path.


## Daily recipes

```bash
just install
just profile copilot
just config
just doctor
just test
just uninstall
```
