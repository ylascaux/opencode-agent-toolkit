# Installation

`just` is the primary command surface.

## macOS quick start

```bash
brew install just
git clone https://github.com/ylascaux/opencode-agent-toolkit.git
cd opencode-agent-toolkit
just install
just doctor
```

`just install` creates `.env` only when absent, creates `.venv`, installs the scanner/API dependencies, generates both OpenCode configs, validates them and runs the tests.

It does **not** install global packages, use `sudo`, edit your shell startup files or modify `~/.config`.

## Optional user command: run from anywhere

`just run` works from inside the toolkit repository. For day-to-day use across many repositories, install the reversible `oc` command:

```bash
just install-user
```

This creates only:

```text
~/.local/bin/oc -> <toolkit>/scripts/opencode-agents
```

The launcher does not `cd` into the toolkit. It preserves your current working directory, so this works as expected:

```bash
cd ~/Projects/my-api
oc
```

OpenCode uses `~/Projects/my-api` as the workspace while loading the toolkit configuration and model mappings from the toolkit repository.

Check the link:

```bash
just user-status
```

Remove it safely:

```bash
just uninstall-user
```

The uninstall command removes the path only when it is a symlink pointing to this toolkit. It refuses to delete unrelated files or symlinks.

If `oc` is already used on your machine, choose another name:

```bash
just install-user opencode-agents
```

The default destination is `~/.local/bin`. Override it without modifying your shell configuration:

```bash
OPENCODE_TOOLKIT_BIN_DIR="$HOME/bin" just install-user
```

If the chosen bin directory is not in `PATH`, the installer only prints a warning; it never edits your shell automatically.

If you move the toolkit repository later, run `just uninstall-user` before the move and `just install-user` after it so the symlink points to the new path.

## Configure models automatically

The toolkit can discover the models exposed by an OpenAI-compatible LiteLLM gateway:

```bash
export LITELLM_BASE_URL="https://gateway.example.com"
export LITELLM_API_KEY="..."
just configure
```

The configurator discovers `/v1/models`, recommends models for `fast`, `general`, `coding`, `reasoning`, `deep`, `review` and `security`, then maps those profiles to all 37 `MODEL_*` variables. Interactive overrides are supported.

Non-interactive: `just configure --auto`

Dry-run: `just configure --auto --dry-run`

Offline/saved response: `just configure --models-file ./models.json`

### Cloudflare Access / custom headers

Model discovery reads, but never persists, these process variables:

```bash
export CF_ACCESS_TOKEN="..."
export LITELLM_HEADERS_JSON='{"x-custom-header":"value"}'
just configure
```

`CF_ACCESS_TOKEN` is sent as `cf-access-token`. API keys and access tokens are not written to `.env` by the configurator.

## Runtime selection

`.env` supports `OPENCODE_MAJOR=1`, `2`, or `auto`. One-off selection is available through `just v1` and `just v2`.

## Daily recipes

```bash
just install
just install-user
just user-status
just uninstall-user
just configure
just doctor
just run
just check
just test
just scan
just api
just models
just refresh
just clean
```
