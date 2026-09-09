# Git-backed long-term memory

The toolkit can inject a small, user-controlled long-term memory into generated agent prompts. The feature is **disabled by default** and works in both OpenCode V1 and V2 because memory is rendered before reliability policies are applied.

## Design

The memory repository is a private Markdown/JSON repository with four scopes:

```text
projects/   durable project context, decisions and conventions
workstyle/  cross-project preferences
hats/       reusable working lenses mapped to toolkit agents
inbox/      future candidates; never injected by default
```

Agents receive rendered text only. They do not receive direct filesystem or Git write access to the memory repository.

Memory context cannot grant permissions, bypass plan approval, weaken sandbox policy, or override explicit repository/user instructions.

## Enable it

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

Disable it at any time:

```bash
just memory-off
```

Force a refresh:

```bash
just memory-sync
```

`memory-on` stores the enable flag and optional repository URL in `.env.local`, so profile switching does not overwrite it.

## Project matching

The toolkit detects the current Git root and `origin` remote. `projects/index.json` can map repository names/remotes to a stable memory project id:

```json
{
  "version": 1,
  "projects": [
    {
      "id": "opencode-agent-toolkit",
      "match": {
        "names": ["opencode-agent-toolkit"],
        "remotes": ["ylascaux/opencode-agent-toolkit"]
      }
    }
  ]
}
```

If no explicit mapping matches, `projects/<git-root-name>/` is used when it exists. `OAT_MEMORY_PROJECT` can force an id.

Only Markdown files at the root of the matched project directory are injected. `sessions/` and `inbox/` are intentionally excluded from automatic context.

## Hats

`hats/assignments.json` maps an agent to one or more hats:

```json
{
  "version": 1,
  "default": [],
  "agents": {
    "orchestrator": ["architect", "software-engineer"],
    "platform-architect": ["architect", "platform-engineer"]
  }
}
```

A hat is stored as `hats/<name>.md`. It describes priorities and working habits; it does not replace the technical role or permission map.

`OAT_MEMORY_EXTRA_HATS=foo,bar` adds extra hats to all mapped agents for a run.

## Sync and context limits

Relevant settings:

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

## Sandbox behavior

Memory is prepared on the trusted host before OpenCode starts. The private memory clone is **not mounted into the execution sandbox**. Sandboxed agents see only the rendered text already present in their generated prompt.

## Phase 1 write policy

Phase 1 is intentionally read-only from the agent runtime. Automatic conversation extraction, confidence scoring, consolidation and Git commits should be implemented as a separate controlled pipeline later. This prevents a single conversation or compromised project from silently rewriting durable personal memory.

Because the repository is plain Markdown, it can later be opened directly as an Obsidian vault without changing the toolkit storage format.
