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
