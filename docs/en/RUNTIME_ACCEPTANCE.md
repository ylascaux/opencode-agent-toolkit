# Runtime acceptance

`scripts/runtime-acceptance` validates the integrated local multi-runtime workflow from a disposable external Git repository and a disposable copy of the toolkit.

The command writes a synthetic `.env`, isolates `HOME` and all XDG directories, and forwards only a small allowlist of non-secret environment variables. The developer checkout, its `.env` / `.env.local`, generated artifacts, private memory vault, and normal OpenCode state are never used as mutable acceptance state.

## Mandatory core acceptance

The mandatory CI jobs run `scripts/runtime-acceptance` with `OAT_ACCEPTANCE_SKIP_MEMORY=1`. This is an explicit skip, not a synthetic MCP implementation. The harness validates:

- OpenCode V1/V2 launcher routing from an external project;
- portable toolkit skill-source registration in the launcher config;
- Codex install/doctor/conflict/uninstall behavior;
- the exact user-owned skill-directory regression (`references/user.txt` without a `SKILL.md`);
- managed-file drift protection;
- manifest v1 compatibility;
- Docker/DinD isolation policy.

The Docker job additionally starts the actual OpenCode V2 CLI from `/workspace` in the freshly built runtime image and queries the authenticated `GET /api/skill` endpoint with the requested project location. The live smoke validates server startup, transport authentication, location resolution, and the V2 response shape without invoking a model or using a synthetic OpenCode response. Skill-source injection itself remains covered deterministically by the launcher acceptance because the beta CLI's returned discovery contents are not a stable contract across beta builds.

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

For the real OpenCode V2 HTTP smoke, build the image from the current checkout and run:

```bash
docker build -t opencode-agent-toolkit:acceptance -f runtime/Dockerfile .
OAT_RUNTIME_IMAGE=opencode-agent-toolkit:acceptance \
  python3 -B scripts/opencode-v2-skill-smoke
```

Acceptance resources are temporary and Docker smoke containers are removed on exit.
