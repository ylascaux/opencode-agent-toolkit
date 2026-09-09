# External Git-backed memory

`opencode-agent-toolkit` no longer owns the memory implementation. Memory is provided by the standalone **`ylascaux/opencode-memory-plugin`** repository, while durable personal/project data stays in a separate private Git repository such as `ylascaux/opencode-memory`.

```text
opencode-agent-toolkit
        │ configures / consumes
        ▼
opencode-memory-plugin
        │ reads / curates
        ▼
private opencode-memory repository
```

This keeps agent orchestration, the OpenCode runtime adapter, and private user data independently versioned.

## Compatibility

The plugin exposes dedicated OpenCode V1 and V2 adapters around the same memory core.

| Capability | OpenCode V1 | OpenCode V2 beta |
| --- | --- | --- |
| Automatic candidate capture | yes | yes |
| Project/workstyle/hats storage | yes | yes |
| Candidate review/promote lifecycle | yes | yes |
| Native plugin prompt injection | yes | not exposed by the V2 API yet |
| Toolkit prompt injection | not needed | yes |

V1 uses `experimental.chat.system.transform` directly. V2 currently has no equivalent plugin hook, so the toolkit calls the plugin's stable `render` CLI while generating V2 agent prompts. The memory logic still lives entirely in the external plugin.

## Enable

After `just install`:

```bash
just memory-on git@github.com:USER/opencode-memory.git
just memory-status
```

The external plugin is cloned automatically from `git@github.com:ylascaux/opencode-memory-plugin.git` into:

```text
${XDG_DATA_HOME:-$HOME/.local/share}/opencode-agent-toolkit/plugins/opencode-memory-plugin
```

The bootstrap ref is `main`. Once a release is tagged, pin it explicitly:

```bash
OAT_MEMORY_PLUGIN_REF=v0.1.0
```

This is preferable for reproducible toolkit runs.

## Automatic capture

Capture is independent from memory reads and is disabled by default:

```bash
just memory-capture-on
```

Both V1 and V2 extract only bounded user/assistant text. Reasoning, shell output and tool output are not persisted. Extracted observations go only to the local candidate quarantine.

```text
session
  │
  ▼
local candidate
  │ explicit human accept
  ▼
inbox/accepted        # still inactive
  │ explicit human promote
  ▼
projects/workstyle/hats
  │ explicit push
  ▼
private Git remote
```

Session events never commit or push the private memory repository.

## Candidate workflow

```bash
just memory-candidates
just memory-candidate a31f92d780cc
just memory-reject a31f92d780cc
just memory-accept a31f92d780cc
just memory-promote a31f92d780cc
just memory-push
```

Override the promotion target when needed:

```bash
just memory-promote a31f92d780cc workstyle/preferences.md
```

`push=true` can be passed to `memory-accept` or `memory-promote`, but explicit separate pushes are safer and remain the default.

## Manual candidate

```bash
just memory-add workstyle \
  'Prefer Just' \
  'Prefer Justfiles over Makefiles for project automation.' \
  --target workstyle/preferences.md
```

## Rendered context

Inspect exactly what an agent receives:

```bash
just memory-show orchestrator
```

The external plugin resolves the current Git repository, maps it through `projects/index.json`, loads project memory, cross-project workstyle and the hats assigned to the named agent, then bounds the result by `OAT_MEMORY_MAX_CHARS`.

## Configuration

Toolkit/plugin integration:

```bash
OAT_MEMORY_PLUGIN_REPO=git@github.com:ylascaux/opencode-memory-plugin.git
OAT_MEMORY_PLUGIN_REF=main
OAT_MEMORY_PLUGIN_AUTO_SYNC=1
OAT_MEMORY_PLUGIN_SYNC_INTERVAL_SECONDS=300
```

Private vault:

```bash
OAT_MEMORY_ENABLED=0
OAT_MEMORY_REPO=git@github.com:USER/opencode-memory.git
OAT_MEMORY_AUTO_SYNC=1
OAT_MEMORY_SYNC_INTERVAL_SECONDS=300
OAT_MEMORY_MAX_CHARS=12000
OAT_MEMORY_STRICT=0
```

Capture:

```bash
OAT_MEMORY_CAPTURE_ENABLED=0
OAT_MEMORY_CAPTURE_MAX_INPUT_CHARS=18000
OAT_MEMORY_MAX_CANDIDATES_PER_SESSION=5
# OAT_MEMORY_EXTRACTOR_MODEL=provider/model
```

The standalone plugin also supports canonical `OPENCODE_MEMORY_*` variables. The `OAT_MEMORY_*` aliases are retained so toolkit upgrades are backward compatible, including the toolkit's existing default vault at `~/.local/share/opencode-agent-toolkit/memory`.

## Failure behavior

Plugin and memory Git operations are non-interactive. Automatic updates use `fetch` plus `pull --ff-only` or an explicit detached tag/ref. A dirty local plugin checkout is never overwritten automatically.

The memory vault must be clean before `accept` or `promote`. Promotion targets are allowlisted and cannot escape the vault. A failed push never rolls back an already-valid local commit.

## Sandbox boundary

The private memory repository is not mounted into the toolkit execution sandbox. V2 receives only rendered prompt text. V1 receives memory through the OpenCode plugin hook, not by granting agent shell access to the vault.

## Ownership boundary

The toolkit should not grow memory extraction/storage logic again. Changes to capture, candidate scoring, Git curation, retrieval or future V2 context-source support belong in `opencode-memory-plugin`; this repository owns only installation/configuration and the temporary V2 rendering bridge.
