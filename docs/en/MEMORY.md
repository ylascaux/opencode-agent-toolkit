# Git-backed long-term memory

The toolkit can inject a small, user-controlled long-term memory into generated agent prompts. Read-side memory is **disabled by default** and works in OpenCode V1 and V2. Automatic candidate capture is a separate opt-in feature and targets OpenCode V2.

## Design

The private memory repository stays human-readable Markdown/JSON:

```text
projects/   durable project context, decisions and conventions
workstyle/  cross-project working preferences
hats/       reusable working lenses mapped to agents
inbox/      accepted/promoted candidates; never injected directly
```

Agents receive rendered text only. The private Git clone is not mounted into the sandbox and the agent runtime has no direct write access to it.

Memory cannot grant permissions, bypass plan approval, weaken sandbox policy, or override explicit repository/user instructions.

## Enable read-side memory

After `just install`:

```bash
just memory-on git@github.com:USER/opencode-memory.git
just memory-status
just memory-show orchestrator
```

The repository is cloned by default to:

```text
${XDG_DATA_HOME:-$HOME/.local/share}/opencode-agent-toolkit/memory
```

Disable or force a refresh with:

```bash
just memory-off
just memory-sync
```

`memory-on` stores its settings in `.env.local`.

## Project matching

The toolkit detects the current Git root and `origin` remote. `projects/index.json` maps repository identities to stable memory project ids. If no explicit mapping matches, `projects/<git-root-name>/` is used when it exists. `OAT_MEMORY_PROJECT` can force an id.

Only Markdown files at the root of the matched project directory are injected. `sessions/` and `inbox/` are excluded from automatic context.

## Hats

`hats/assignments.json` maps agents to `hats/<name>.md`. A hat describes priorities and working habits; it does not replace the technical role or permission map.

`OAT_MEMORY_EXTRA_HATS=foo,bar` adds temporary hats to mapped agents.

## Automatic candidate capture (V2)

Enable it only after memory itself is enabled:

```bash
just memory-capture-on
```

The V2 plugin listens for the current `session.status` event when the status becomes `idle`, plus the deprecated `session.idle` event for compatibility. Both paths are deduplicated by conversation hash.

At session completion the plugin:

1. reads only user/assistant text;
2. ignores tool outputs, shell messages and reasoning content;
3. bounds extractor input;
4. asks the extraction model only for durable facts/preferences;
5. deterministically rejects several common secret formats;
6. stores structured candidates only, never raw transcripts.

Local candidates live by default under:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/opencode-agent-toolkit/memory/
├── candidates/
├── accepted/
├── rejected/
└── promoted/
```

The extractor uses `OAT_MEMORY_EXTRACTOR_MODEL`, then `MODEL_LOW`. Capture is fail-open unless `OAT_MEMORY_CAPTURE_STRICT=1`; a memory extractor failure should not break normal development work.

Main settings:

```bash
OAT_MEMORY_CAPTURE_ENABLED=0
OAT_MEMORY_CAPTURE_STRICT=0
OAT_MEMORY_CAPTURE_MAX_INPUT_CHARS=18000
OAT_MEMORY_MAX_CANDIDATES_PER_SESSION=5
# OAT_MEMORY_EXTRACTOR_MODEL=github-copilot/gpt-5.6-luna
```

Repeated observations of the same pending candidate increment `occurrences` and update `last_seen_at` instead of creating duplicates.

For V1 or manual workflows:

```bash
just memory-add decision "Title" "Durable decision" --target project/decisions.md
```

## Review and trust lifecycle

List and inspect candidates:

```bash
just memory-candidates
just memory-candidate abcdef123456
```

Rejecting remains local and never touches Git:

```bash
just memory-reject abcdef123456
```

Acceptance is an explicit user action. It creates a provenance note under `inbox/accepted/` and a **local** Git commit. `inbox/` is still excluded from injected context:

```bash
just memory-accept abcdef123456
```

Push immediately only when requested:

```bash
just memory-accept abcdef123456 push=true
```

Promotion is a second explicit action. It appends the memory to an injected target (`projects/`, `workstyle/` or `hats/`) and moves the provenance note to `inbox/promoted/`:

```bash
just memory-promote abcdef123456
# or explicit target
just memory-promote abcdef123456 project/decisions.md push=true
```

Allowed targets are `project/context.md`, `project/decisions.md`, `project/conventions.md`, `project/known-issues.md`, `project/current.md`, the four standard `workstyle/*.md` files, or `hat:<name>`.

Push existing local curation commits with:

```bash
just memory-push
```

Acceptance/promotion refuses to run when the memory clone already has uncommitted changes. Sync remains fast-forward only.

## Sync and context limits

```bash
OAT_MEMORY_ENABLED=0
OAT_MEMORY_REPO=git@github.com:USER/opencode-memory.git
OAT_MEMORY_AUTO_SYNC=1
OAT_MEMORY_SYNC_INTERVAL_SECONDS=300
OAT_MEMORY_MAX_CHARS=12000
OAT_MEMORY_STRICT=0
```

Automatic Git pull is throttled by a timestamp in the clone's `.git` directory. Failed sync uses the last local snapshot and warns unless `OAT_MEMORY_STRICT=1`.

The rendered context is bounded. By default roughly 75% of the character budget is reserved for project/workstyle memory and 25% for hats.

## Security model

```text
OpenCode V2 conversation
        │
        ▼
 conservative extractor
        │
        ▼
local candidate (not Git)
   │             │
 reject          explicit accept
   │             │
   ▼             ▼
local/rejected   Git inbox/accepted
                      │
                explicit promote
                      │
                      ▼
             projects/workstyle/hats
```

No session event automatically commits or pushes the memory repository. Capture may create a candidate; only a user command can put it into Git, and a second explicit command is required before it becomes injected durable memory.

Because storage remains plain Markdown, the repository can be opened directly as an Obsidian vault.
