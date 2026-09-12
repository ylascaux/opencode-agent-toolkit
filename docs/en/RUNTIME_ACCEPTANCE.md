# Runtime acceptance

`scripts/runtime-acceptance` validates the integrated local multi-runtime workflow from a disposable external Git repository.

The command copies the toolkit into a temporary directory, writes a synthetic `.env`, isolates `HOME` and all XDG directories, and forwards only a small allowlist of non-secret environment variables. The developer checkout, its `.env` / `.env.local`, generated artifacts, private memory vault, and normal OpenCode state are never used as acceptance state.

## Mandatory core acceptance

The mandatory CI jobs run with `OAT_ACCEPTANCE_SKIP_MEMORY=1`. This is an explicit skip, not a synthetic MCP implementation. They still validate:

- OpenCode V1/V2 launcher routing from an external project;
- portable toolkit skill-source registration;
- Codex install/doctor/conflict/uninstall behavior;
- the exact user-owned skill-directory regression (`references/user.txt` without a `SKILL.md`);
- managed-file drift protection;
- manifest v1 compatibility;
- Docker/DinD isolation policy.

The Docker job also starts the current OpenCode V2 runtime from the external project and uses a real V2 plugin calling `ctx.skill.list()` to verify both the canonical toolkit skills and a project-local skill are actually discovered.

## Real private memory MCP acceptance

The harness never fabricates the memory tool surface. When `OAT_ACCEPTANCE_MEMORY_PLUGIN_DIR` (or `OAT_MEMORY_PLUGIN_DIR`) points to a prebuilt real `opencode-memory-plugin` checkout, it starts the real stdio MCP service and verifies the five portable tools. It confirms that accept/promote/push are not exposed and does not require a private memory vault.

Because `opencode-memory-plugin` is a separate private repository, the toolkit repository's default `GITHUB_TOKEN` cannot checkout it. CI therefore has a dedicated `private-memory` acceptance job. If repository secret `OAT_MEMORY_PLUGIN_TOKEN` is configured, that job checks out the exact revision pinned in `config/plugins.json`, builds it, and runs the real MCP acceptance. Without the secret the private integration step is explicitly skipped; it is never replaced with a fake server.

Example after a normal local toolkit installation:

```bash
OAT_ACCEPTANCE_MEMORY_PLUGIN_DIR="$HOME/.local/share/opencode-agent-toolkit/opencode-memory-plugin" \
  python3 -B scripts/runtime-acceptance
```

To intentionally run only the non-memory contracts:

```bash
OAT_ACCEPTANCE_SKIP_MEMORY=1 python3 -B scripts/runtime-acceptance
```

For the real OpenCode V2 discovery smoke, provide a freshly built runtime image:

```bash
OAT_ACCEPTANCE_SKIP_MEMORY=1 \
OAT_ACCEPTANCE_DOCKER=1 \
OAT_RUNTIME_IMAGE=opencode-agent-toolkit:acceptance \
  python3 -B scripts/runtime-acceptance
```

Acceptance resources are temporary and Docker probe containers are removed on exit.
