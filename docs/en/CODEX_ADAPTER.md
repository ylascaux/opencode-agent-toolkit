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
- There is no Codex implementation of OpenCode's reliability plugins, queue, stall detection, retry guards, cost limits, or memory integration.
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

The implemented bundle above is local and reversible. Future additions may include portable skills or explicitly rendered memory context; they are not generated today.

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
- reliability intent and explicit portability limits (no memory integration yet).

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

## Memory integration — future milestone

A future adapter integration must use `opencode-memory-plugin`; it must not reimplement extraction or storage. No read/proposal/MCP path below is available in this milestone.

### Read path

Conceptually:

```text
current project
   -> opencode-memory-plugin project resolution
   -> rendered bounded context
   -> Codex instructions/context
```

A generated runtime receives only rendered context, never direct shell access to the private vault by default.

### Write path

Codex may submit a candidate through a portable proposal interface.

Target behavior:

```text
Codex session
   -> memory.propose(...)
   -> local candidate quarantine
   -> explicit human accept/promote
   -> optional explicit push
```

No agent session should directly commit/push promoted memory as an implicit completion step.

### MCP direction

A small MCP server around `opencode-memory-plugin` is a reasonable target if it provides a cleaner common surface for OpenCode and Codex.

Suggested tools:

```text
memory_status
memory_search
memory_render
memory_propose
memory_candidates
```

Mutation-heavy actions such as promote/push should remain human-oriented CLI actions unless a later permission design explicitly authorizes them.

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

`oc sync codex --verbose` reports each agent's resolved tier/model/reasoning policy and capability limitations; dry-run includes the same details. Ordinary sync and check print a concise permission/delegation warning. `runtime.json` records the full toolkit report. The expanded report below remains a future example: it must not be read as a claim that skills or memory integration are available today.

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

Steps 1-6 are implemented. Steps 7-10 remain future milestones.

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
