# Codex adapter specification

## Purpose

The Codex adapter compiles the toolkit's canonical agent definitions into artifacts and optional remote resources that Codex can consume.

It must reuse the same normalized agent graph as OpenCode. It must not introduce a parallel Codex-only agent catalog.

## Confirmed OpenAI capabilities

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

## First implementation target

The first useful Codex adapter should be **local and reversible**.

Recommended generated outputs:

```text
.generated/codex/
  AGENTS.md
  agents/
    <agent-name>.md
  skills/
    <skill-name>/...
  runtime.json
  memory-context.md        # only when explicitly rendered; never committed with private data
```

If Codex expects a repository-root `AGENTS.md`, `oc sync codex` may generate or update a managed section in a root/runtime-specific target, but the canonical content must come from toolkit sources.

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
- memory policy;
- reliability intent.

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

Do not commit a model slug as the permanent meaning of `low`, `medium`, or `high`.

### Reasoning tiers

Keep reasoning separate from model quality.

Portable policy:

```text
low | medium | high | xhigh
```

An adapter may clamp unsupported values and must report that clamp in verbose/dry-run output.

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

## Skills

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

## Memory integration

The adapter must integrate with `opencode-memory-plugin`; it must not reimplement extraction or storage.

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

## Remote Agent API integration

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

`oc sync codex --verbose` should explain portability gaps.

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

Do not implement steps 8-10 before local generation is stable and tested.

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
