# Runtime acceptance

`scripts/runtime-acceptance` validates the integrated local multi-runtime workflow from a disposable external Git repository.

The command copies the toolkit into a temporary directory, writes a synthetic `.env`, isolates `HOME` and all XDG directories, and forwards only a small allowlist of non-secret environment variables. The developer checkout, its `.env` / `.env.local`, generated artifacts, private memory vault, and normal OpenCode state are never used as acceptance state.

A prebuilt real `opencode-memory-plugin` checkout is required through `OAT_ACCEPTANCE_MEMORY_PLUGIN_DIR` (or the existing `OAT_MEMORY_PLUGIN_DIR`). The acceptance suite starts the real stdio MCP service and verifies the five portable tools; it does not expose accept/promote/push or require a private memory vault.

Default acceptance validates OpenCode V1/V2 launcher routing, portable skill-source registration, Codex install/doctor/conflict/uninstall behavior, manifest v1 compatibility, the real memory MCP protocol, and Docker/DinD isolation policy without model-provider credentials.

Set `OAT_ACCEPTANCE_DOCKER=1` with `OAT_RUNTIME_IMAGE=<fresh image>` to add a real OpenCode V2 discovery smoke. That probe starts the actual runtime image against a temporary external project and uses the V2 plugin API (`ctx.skill.list()`) to verify both toolkit skills and a project-local skill are registered.

CI checks out and builds the memory plugin at the exact revision pinned by `config/plugins.json`, then runs both the offline and Docker acceptance jobs.

Example after a normal local toolkit installation:

```bash
OAT_ACCEPTANCE_MEMORY_PLUGIN_DIR="$HOME/.local/share/opencode-agent-toolkit/opencode-memory-plugin" \
  python3 -B scripts/runtime-acceptance
```

Acceptance resources are temporary and Docker probe containers are removed on exit.
