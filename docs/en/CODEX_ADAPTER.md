# Codex adapter specification

## Purpose

The local Codex adapter compiles the toolkit's canonical agent definitions into a staged, disposable instruction/configuration bundle. Remote resources remain a future direction, not a dependency or side effect of local synchronization.

It must reuse the same normalized agent graph as OpenCode. It must not introduce a parallel Codex-only agent catalog.

## Implemented local workflow

```bash
oc sync codex --dry-run
oc sync codex
oc sync codex --check
oc sync codex --verbose
```

`CodexAdapter` consumes the same `NormalizedAgent` graph as `OpenCodeAdapter`; it does not parse a second agent catalog. The common artifact plan drives generation, dry-run, and drift detection. Dry-run reports intended changes without filesystem writes. Check exits non-zero for drift and never repairs it. Repeated synchronization with identical sources and exported configuration is deterministic.

The generated bundle is contained in the toolkit checkout:

```text
.generated/codex/
  AGENTS.md                 # compact operating instructions
  agents/
    <agent-name>.md        # composed instructions and policy intent
    <agent-name>.toml      # native local custom-agent configuration
  runtime.json              # toolkit report, NOT native Codex configuration
```

Markdown and TOML include generated-file notices; JSON carries generated metadata without invalid comments. No root `AGENTS.md`, personal Codex configuration, memory context, MCP server, or remote resource is created. Keep edits in canonical sources, not this bundle.

### Opt-in use in a project

Synchronization stages files; it does **not** install or launch Codex or change the current session's default agent. After inspecting the bundle:

1. Copy or link the selected generated TOML files into the target project's `.codex/agents/`. Check each destination first; do not overwrite existing personal/project agents. Select the graph's required lead and child roles together. Each TOML embeds its complete instructions; the adjacent Markdown is a readable representation, not a required relative file dependency. If using Markdown instead of an installed native role, explicitly read the assigned file from the toolkit checkout, not a same-named path in the target project.
2. Start a new Codex session in the target project and explicitly ask it to read the generated `AGENTS.md` using its absolute toolkit path. Preserve the project's own root instructions.
3. Ask for the desired toolkit role explicitly. Installing `meta-router.toml` does not automatically make it the root/default agent.
4. Inspect the selected permission mode before delegating and verify the intended roles and model settings in your local client.

Codex discovers project custom agents under `.codex/agents/`; the generated TOML uses `name`, `description`, `developer_instructions`, and supported model/sandbox settings. Live parent permission overrides can supersede a custom agent's sandbox default. See the [official local subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents). The staged `.generated/codex/AGENTS.md` is not on a typical project's root-to-working-directory discovery path, hence the explicit read above; see [instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

For rollback, remove only the project links/copies you deliberately installed. Staged outputs are disposable and can be regenerated; synchronization does not manage those opt-in installations or unrelated project files. A copied agent must be refreshed manually after regeneration; a link follows the staged source. Sync removes obsolete staged `agents/*.md` and `agents/*.toml` only when their first line bears the toolkit's generated notice. Unmarked user additions are preserved; symlinked output paths are rejected rather than followed.

### Local portability limits

- The graph-derived child allowlist and step budget are instructions, not a native per-role allowlist or deterministic watchdog. Leaves disable delegation with `[agents] enabled = false` in their native TOML.
- Canonical `allow` / `ask` / `deny` rules are retained as policy instructions. Only canonical `edit: allow` receives a `workspace-write` sandbox default; both `ask` and `deny` conservatively receive `read-only`. Coarse sandbox defaults do not reproduce OpenCode shell-pattern approvals, sensitive-path rules, or tool permissions exactly. Parent runtime overrides still matter; do not treat the generated policy report as an enforcement engine.
- There is no Codex implementation of OpenCode's reliability plugins, queue, stall detection, retry guards, or cost limits. Portable memory uses the separate optional local MCP service described below.
- No canonical local `SKILL.md` sources are currently tracked. The report therefore lists zero mapped skills; agent prompts and OpenCode plugins are not repackaged as fictional Codex skills. Skill-source mapping is deferred until portable canonical skill sources exist.
- Model availability is not checked remotely. Choose model/reasoning combinations supported by your local Codex setup; generation itself makes no model or OpenAI API calls.

## Future remote building blocks

As of September 2026, OpenAI documents the following building blocks relevant to this adapter:

- instruction files such as `AGENTS.md` influence model behavior;
- reusable Agents can declare a model, reasoning configuration and `multi_agent.max_concurrent_subagents`;
- Skills are first-class versioned resources and can be attached to hosted environments;
- GPT coding models expose configurable reasoning levels.

References:

- https://developers.openai.com/api/docs/guides/latest-model
- https://developers.openai.com/api/reference/typescript/resources/beta/subresources/agents/methods/create
- https://developers.openai.com/api/reference/typescript/resources/skills/methods/list
- https://developers.openai.com/api/reference/cli/resources/skills/subresources/versions/methods/create

The implementation must prefer documented APIs. Do not infer undocumented Codex CLI configuration formats from examples or old versions.

## Future bundle extensions

The implemented bundle above is local and reversible. Future additions may include portable skills; they are not generated today. Private memory remains runtime retrieval through the external service.

Possible future additions:

```text
.generated/codex/
  skills/
    <skill-name>/...
  memory-context.md        # only when explicitly rendered; never committed with private data
```

Root instruction management is not implemented; local synchronization leaves existing root instructions untouched.

Remote OpenAI Agent/Skill publication is a later optional mode and must not occur as a side effect of ordinary local generation.

## Mapping from canonical agent definition

### Identity and role

Canonical:

```text
agents/<name>/agent.json
agents/<name>/prompt.md
```

Codex output:

- stable agent name;
- description;
- composed instructions;
- parent/delegation metadata;
- quality tier;
- reasoning tier;
- permission summary;
- reliability intent and explicit portability limits; optional external MCP memory requires manual registration.

### Model tiers

The canonical tier remains:

```text
low | medium | high
```

Codex resolves it through local configuration, for example:

```bash
CODEX_MODEL_LOW=<model>
CODEX_MODEL_MEDIUM=<model>
CODEX_MODEL_HIGH=<model>
```

Optional per-agent override:

```bash
CODEX_MODEL_ORCHESTRATOR=<model>
```

Sync reads **exported environment variables only**, before the OpenCode launcher sources `.env` / `.env.local` or checks Docker/providers. It does not load those files automatically. For example, prefix a sync command with `CODEX_MODEL_LOW=<local-model-id>` or export your chosen tier variables in your shell.

Model precedence is `CODEX_MODEL_<AGENT>` → optional `codex.model` → `CODEX_MODEL_<TIER>` → omit the native model setting and inherit Codex's local model. The agent suffix comes from canonical `model_env` with `MODEL_` removed. Codex mappings do not change existing OpenCode `MODEL_*` profiles.

Do not commit a model slug as the permanent meaning of `low`, `medium`, or `high`.

### Reasoning tiers

Keep reasoning separate from model quality.

Portable policy:

```text
low | medium | high | xhigh
```

Local reasoning mapping defaults to the canonical tier. Model-specific support is the user's configuration responsibility; the adapter does not silently clamp a setting based on a guessed model capability.

Reasoning precedence is `CODEX_REASONING_<AGENT>` → optional `codex.reasoning` → `CODEX_REASONING_<TIER>` → canonical tier. Supported configuration values are `low`, `medium`, `high`, and `xhigh`; invalid values fail before writing. The optional `codex` extension accepts only `model` and `reasoning`, and can be omitted entirely. Other keys are rejected, not forwarded to native configuration.

Example:

```text
repo-researcher: model=low, reasoning=low
builder:         model=medium, reasoning=medium
orchestrator:    model=high, reasoning=high
review-lead:     model=high, reasoning=high
```

### Delegation

The current toolkit graph is authoritative.

```text
meta-router -> lead/orchestrator -> leaf
```

Codex must not gain permission to create arbitrary child roles outside the validated graph merely because the runtime supports generic subagents.

Generated instructions should clearly state:

- which children a lead may delegate to;
- leaf agents may not delegate;
- completed handoffs should be reused;
- independent review is allowed to re-read primary evidence;
- maximum concurrency is a runtime limit, not a reason to fill every slot.

Where the OpenAI Agent API is used, `multi_agent.max_concurrent_subagents` should be derived from toolkit reliability configuration when practical.

## Permissions

OpenCode and Codex have different tool/approval models. The adapter therefore maps **intent**, not syntax.

Canonical effects:

```text
allow
ask
deny
```

Codex mapping must preserve at least these invariants:

- destructive commands remain denied or approval-gated;
- secret/private paths are not silently exposed;
- leaf delegation remains disabled;
- write-capable agents are explicit;
- reviewer/researcher roles remain read-only unless their canonical definition says otherwise.

If Codex cannot deterministically express one permission, generation must surface a warning.

## AGENTS.md generation

`AGENTS.md` should contain stable operating instructions, not project memory dumps.

Recommended sections:

```text
# Generated runtime instructions
## Source of truth
## Agent topology
## Routing rules
## Evidence discipline
## Git safety
## Testing expectations
## Memory integration
## Runtime limitations
```

Avoid embedding:

- full session history;
- private memory repository contents;
- secrets;
- transient model names when a tier can express the requirement;
- generated data that another file already owns.

## Skills — future source mapping

A skill should be portable when it represents reusable domain/workflow knowledge rather than OpenCode plugin behavior.

Possible sources include toolkit skills/plugins/docs that can be cleanly packaged without runtime-specific assumptions.

The adapter should classify each candidate as:

```text
portable
opencode-only
codex-only
unsupported
```

A future publish command may upload portable Codex Skills as versioned OpenAI resources:

```bash
oc sync codex --publish-skills
```

Publishing must be explicit because it mutates remote state.

Local generation remains the default.

## Memory integration — PR5

Portable memory is implemented in [opencode-memory-plugin PR #10](https://github.com/ylascaux/opencode-memory-plugin/pull/10). `config/plugins.json` pins tested commit `650e37665599ef7abd3d2c6d8ee94128ee37f493`. The toolkit consumes that package; no vault, rendering, candidate persistence, or MCP protocol implementation is duplicated here. No new npm publication is assumed.

```text
OpenCode V1/V2 -> native plugin --+
                                 |
Codex -> local stdio MCP --------+-> shared memory implementation -> private vault
                                 |                           \-> local quarantine
human memory CLI ---------------+
```

OpenCode retains native context injection where supported and its existing session capture. V2 retains toolkit-assisted context rendering. MCP is optional for OpenCode. The human CLI remains unchanged: `oc memory show [agent]` renders context, `oc memory candidate ID` inspects one candidate, and `oc memory accept/promote/push` manage the explicit lifecycle.

### Local server setup

Install/build the pinned external plugin and synchronize the host-local vault explicitly through the existing human workflow, using exported configuration:

```bash
python3 /absolute/path/opencode-agent-toolkit/scripts/memory sync
```

`oc memory sync` uses the configured host or Docker runtime. The MCP wrapper requires a host-visible built plugin and the same existing vault/quarantine. Default Docker bind mounts can already make these available on the host. If `OAT_DATA_DIR` or `OAT_STATE_DIR` is customized, map the corresponding host paths through `OAT_MEMORY_PLUGIN_DIR`, `OAT_MEMORY_DIR`, and `OAT_MEMORY_CANDIDATE_DIR`; do not create a second memory store. To use a separate tested plugin checkout, export `OAT_MEMORY_PLUGIN_DIR` pointing to its built checkout. Export the existing memory configuration in the environment launching Codex, including `OAT_MEMORY_ENABLED=1` or its `OPENCODE_MEMORY_ENABLED` equivalent.

Start the server directly, or through the early local routing path:

```bash
/absolute/path/opencode-agent-toolkit/scripts/memory-mcp --cwd /absolute/path/project
oc memory mcp --cwd /absolute/path/project
```

Both paths use the prebuilt external CLI (`oc-memory mcp --cwd PROJECT`) and preserve stdio. They do not load `.env`, `.env.local`, shell profiles, Docker, providers, or generated runtime configuration. They never automatically install/build/clone/sync. Other human `oc memory` commands retain their existing settings-loading behavior. Missing Node, workspace, or built MCP files fail clearly on stderr. To roll back local registration, remove only the MCP server entry you added; native OpenCode/CLI operation remains independent.

### Manual Codex registration

The [official Codex MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) describes local stdio registration using `command`, `args`, `cwd`, forwarded `env_vars`, and optional `enabled_tools`. The following is a reference to add manually to personal or project-local Codex configuration after reviewing existing entries; `oc sync codex` does not generate or install it:

```toml
[mcp_servers.memory]
command = "/absolute/path/opencode-agent-toolkit/scripts/memory-mcp"
args = ["--cwd", "/absolute/path/project"]
cwd = "/absolute/path/project"
env_vars = [
  "OAT_MEMORY_PLUGIN_DIR", "XDG_DATA_HOME", "XDG_STATE_HOME",
  "OAT_MEMORY_ENABLED", "OAT_MEMORY_REPO", "OAT_MEMORY_DIR",
  "OAT_MEMORY_CANDIDATE_DIR", "OAT_MEMORY_PROJECT", "OAT_MEMORY_MAX_CHARS",
  "OAT_MEMORY_EXTRA_HATS", "OAT_MEMORY_CAPTURE_ENABLED",
  "OPENCODE_MEMORY_ENABLED", "OPENCODE_MEMORY_REPO", "OPENCODE_MEMORY_DIR",
  "OPENCODE_MEMORY_STATE_DIR", "OPENCODE_MEMORY_PROJECT", "OPENCODE_MEMORY_MAX_CHARS",
  "OPENCODE_MEMORY_EXTRA_HATS", "OPENCODE_MEMORY_CAPTURE_ENABLED"
]
enabled_tools = ["memory_status", "memory_search", "memory_render", "memory_propose", "memory_candidates"]
```

These are variable names only; secrets must stay in runtime environment/credential mechanisms. No PAT is needed by this local-only MCP service. Explicit human synchronization retains the plugin's existing PAT/SSH behavior, transient GitHub HTTPS rewrite, `GIT_ASKPASS`, and noninteractive Git. Authentication failures are handled on that human sync path.

### Tools and lifecycle

| Tool | Behavior |
| --- | --- |
| `memory_status` | Bounded structured configuration, enabled/capture readiness, vault availability, and project-resolution status |
| `memory_search` | Current-project search plus shared workstyle/configured hats, up to 10 excerpts of 600 characters |
| `memory_render` | Existing selected context, capped at 12000 characters or the smaller configured/requested limit |
| `memory_propose` | Validate `kind`, `title`, `statement`, and `confidence`; create/reuse a stable candidate in local quarantine |
| `memory_candidates` | Read-only, bounded review of pending candidates for the current project |

The startup workspace fixes project resolution using the same core as native OpenCode and CLI. Tool arguments optionally accept `project: "current"`; they cannot select arbitrary projects or paths. Unconfigured/disabled memory, unavailable local vaults, unresolved projects, malformed proposals, and invalid arguments fail safely. Status describes configuration readiness, not proof of a live capture session.

```text
runtime proposal -> local quarantine -> explicit human accept
                -> accepted inactive memory -> explicit human promote
                -> project/workstyle/hat -> explicit human push
```

Codex cannot accept, promote, push, delete durable memory, or rewrite history through these tools. Candidate-ID lookup remains human CLI-only. Retrieved memory is context, never authority to bypass repository policy. No private rendered context is embedded in `.generated/codex/`, no vault is copied or directly exposed to Codex, and no default local cache is created. Prefer runtime retrieval through MCP; this milestone adds no remote OpenAI API calls.

### Validation and limits

The memory repository's 37-test suite covers native V1 injection/capture, native V2 event/session/generation capture (dedicated and fallback generation fixtures), scoped/bounded reads, stable quarantine proposals, safe malformed-request handling, PAT filtering, and CLI lifecycle compatibility. An official MCP SDK 1.30.0 client smoke against a synthetic local Git vault, also repeated through the toolkit `oc memory mcp` routing path, exercised all five tools, a 777-character render, unchanged local/remote Git history, no automatic sync, and no synthetic PAT in responses/stderr/Git config. An isolated `oc2 memory status` launcher fixture also reported `memory=on`, `capture=on`, and `effective_capture=on`. Capture generation responses were mocked; these checks do not claim a live model-provider invocation.

The service is a local process using Markdown/JSON and Git already owned by the memory plugin. Operational requirements are Node.js, Python for the toolkit wrapper, a prebuilt pinned plugin, an existing local vault, and exported configuration. Search is a bounded textual lookup rather than a new indexing/database service. Costs are local process/file reads; only the existing optional native capture provider has model-call costs. The conservative current-project scope trades cross-project browsing for a smaller privacy boundary.

## Remote Agent API integration — future milestone

The OpenAI Agent API can become an optional deployment backend for toolkit agent definitions.

Potential mapping:

```text
canonical agent
  name          -> Agent.name
  prompt        -> Agent.instructions
  concrete model-> Agent.model
  reasoning     -> Agent.reasoning
  concurrency   -> Agent.multi_agent.max_concurrent_subagents
  tools         -> Agent.tools
```

This must be implemented as an explicit remote sync mode, for example:

```bash
oc sync codex --remote
oc sync codex --remote --dry-run
```

Requirements:

- deterministic mapping;
- toolkit metadata stored on each remote resource;
- remote IDs tracked in generated/local state, not in canonical agent definitions;
- update only toolkit-owned remote resources;
- dry-run displays creates/updates/deletes without mutating;
- deletion requires a separate explicit flag or command.

Do not make remote API resources mandatory for using Codex locally.

## Runtime capability report

`oc sync codex --verbose` reports each agent's resolved tier/model/reasoning policy and capability limitations; dry-run includes the same details. Ordinary sync and check print a concise permission/delegation warning. `runtime.json` records the full toolkit report. The expanded report below remains a future example: it must not be read as a claim that skills exist or an MCP server is registered and available. Actual sync reports portable MCP support, registration required, and availability not checked.

Example:

```text
Codex capability report

SUPPORTED
  agent instructions
  model mapping
  reasoning mapping
  bounded subagent concurrency
  portable skills
  rendered memory context

PARTIAL
  shell permission equivalence
  step budgets

UNAVAILABLE / NOT CONFIGURED
  deterministic stall watchdog
  provider cost kill switch
```

The actual report must be generated from implementation capabilities, not hard-coded from this example.

## Git workflow

Codex work should follow the same safe repository rules as OpenCode:

- inspect status before writing;
- create/use a task branch;
- never discard unrelated user changes;
- avoid destructive reset/clean/force operations by default;
- run relevant tests/checks;
- summarize changed files;
- prepare a PR when requested.

Runtime-specific automation may differ, but these policy outcomes remain stable.

## Implementation sequence

Recommended order:

1. extract/identify a normalized internal agent representation;
2. snapshot current OpenCode generated output;
3. refactor OpenCode generation to consume normalization without changing output;
4. add runtime adapter interface;
5. add local Codex generation;
6. add `oc sync` CLI and dry-run/check modes;
7. integrate bounded memory rendering;
8. add portable memory candidate proposal surface;
9. add optional MCP exposure;
10. add optional remote Agent/Skill publication.

Steps 1-9 are implemented: memory retrieval/proposals use the external MCP service and manual local registration. Step 10 remains future work.

## Acceptance criteria

A first Codex adapter PR is acceptable when:

- OpenCode generation is unchanged or intentionally migrated with passing tests;
- Codex artifacts are generated from the same canonical agent directories;
- `oc sync codex --dry-run` performs no writes;
- generation is idempotent;
- model mappings are configurable;
- no private memory vault is copied into generated committed files;
- at least one lead and one leaf demonstrate correct delegation mapping;
- unsupported reliability/permission semantics are reported;
- docs and tests describe the boundary between local Codex integration and optional remote OpenAI Agents/Skills.
