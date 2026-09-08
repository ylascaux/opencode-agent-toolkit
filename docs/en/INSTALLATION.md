# Installation

The toolkit is designed around `just` as its primary command surface.

## Recommended macOS setup

```bash
brew install just
git clone https://github.com/ylascaux/opencode-agent-toolkit.git
cd opencode-agent-toolkit
just install
```

`just install` performs the full bootstrap:

1. creates `.env` from `.env.example` if needed;
2. preserves an existing `.env`;
3. creates `.venv`;
4. installs the project-inventory CLI/API dependencies;
5. generates native OpenCode V1 and V2 configs;
6. validates both configs;
7. runs the repository test suite;
8. checks the selected OpenCode runtime.

It does not overwrite an existing model mapping.

## Without `just`

The bootstrap script itself does not depend on `just`:

```bash
./scripts/bootstrap
./scripts/opencode-agents
```

## Configure models

By default every agent maps to `litellm/smart-router`. Customize only the roles for which you want explicit model selection:

```dotenv
MODEL_META_ROUTER=litellm/fast-router
MODEL_ORCHESTRATOR=litellm/smart-router
MODEL_BUILDER=litellm/coding-model
MODEL_REVIEWER=litellm/reasoning-model
MODEL_DEEP_REASONER=litellm/deep-reasoning-model
MODEL_APPSEC=litellm/security-review-model
```

Inspect the current mapping with:

```bash
just models
```

## Runtime selection

`.env` supports:

```dotenv
OPENCODE_MAJOR=1
```

Values:

- `1`: stable `opencode` with `opencode.jsonc`;
- `2`: OpenCode 2 beta `opencode2` with `opencode.v2.jsonc`;
- `auto`: prefer `opencode2` when installed, otherwise `opencode`.

One-off overrides:

```bash
just v1
just v2
```

## Daily commands

```bash
just                 # list recipes
just install         # first-time setup
just doctor          # environment/config health check
just run             # launch selected runtime
just v1              # force OpenCode V1
just v2              # force OpenCode V2
just check           # generate configs + validate + tests
just test            # repository tests
just scan            # create architecture-inventory.json
just api             # start local inventory API
just models          # show MODEL_* mappings
just refresh         # rebuild venv/dependencies
just clean           # remove generated local state
```

## Health check

```bash
just doctor
```

The doctor reports Python, `just`, OpenCode binaries, `.env`, `.venv`, V1/V2 config validity, tests, `PROJECTS_ROOT`, runtime selection, agent count and command count.

Warnings are non-fatal for optional components such as OpenCode 2 or a missing `~/Projects` directory.
