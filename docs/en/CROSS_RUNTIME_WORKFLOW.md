# Cross-runtime workflow

## Why this document exists

The toolkit should let work move between OpenCode, Codex, and a GitHub-connected assistant without creating three incompatible sources of truth.

The repository owns engineering policy. The memory plugin owns durable contextual memory. Each runtime is only an execution surface.

Local OpenCode and Codex adapters plus `oc sync` are implemented. PR5 adds portable memory through the external local MCP service with manual Codex registration; remote Agents/Skills publication remains future work. OpenCode retains its native V1/V2 memory plugin.

```text
                           Git repository
                   canonical code + agent policy
                              /   |   \
                             /    |    \
                            v     v     v
                      OpenCode  Codex  ChatGPT/GitHub
                            \     |     /
                             \    |    /
                              v   v   v
                       pull requests / reviews
                                 |
                                 v
                      opencode-memory-plugin
```

## What belongs where

### `opencode-agent-toolkit`

Store durable, shareable engineering behavior here:

- agent roles;
- prompts;
- parent/child topology;
- permissions intent;
- model quality tiers;
- reliability policy;
- runtime adapter code;
- schemas/contracts;
- documentation;
- tests.

### `opencode-memory-plugin`

Store memory behavior here:

- candidate extraction;
- candidate quarantine;
- project resolution;
- rendered context;
- promotion rules;
- private-vault Git lifecycle;
- portable application API and local stdio MCP memory surface.

### Private memory repository

Store private durable context here:

- project decisions;
- project facts worth carrying between sessions;
- workstyle preferences;
- hats/personas;
- curated cross-project context.

### Runtime-local/generated state

Store disposable artifacts here:

- generated runtime configuration;
- resolved model mappings;
- remote resource IDs/caches;
- explicit local ephemeral rendered context, when requested (never generated for Codex by default);
- temporary session metadata.

This state must be reproducible or safely discardable.

## Choosing a runtime

Use the runtime that best fits the task, not the runtime where the project was originally created.

### OpenCode

Prefer OpenCode when:

- testing toolkit-specific OpenCode V1/V2 integration;
- validating OpenCode plugins/watchdogs;
- reproducing an OpenCode runtime bug;
- using existing OpenCode-specific orchestration before Codex parity exists.

### Codex

Prefer Codex when:

- implementing/refactoring code in the repository;
- using Codex-native coding workflows;
- evaluating Codex subagent/model strategies;
- implementing the Codex adapter itself;
- comparing cost/quality with OpenCode runtime choices.

### ChatGPT with GitHub access

Prefer a GitHub-connected assistant when:

- preparing architecture/docs/specification changes;
- opening or updating a PR without needing a local runtime;
- reviewing a PR/diff;
- coordinating work that spans repositories;
- transforming design discussion into durable repository documentation.

Do not assume this surface has the same local shell/runtime access as Codex or OpenCode.

## Standard task handoff

For local Codex, prepare the staged bundle with `oc sync codex --dry-run`, generate with `oc sync codex`, and verify with `oc sync codex --check`. From the target project, use `oc codex install` and read-only `oc codex doctor`; `oc codex uninstall` removes only manifest-owned artifacts. Use `oc codex install --with-memory` only for explicit local memory MCP registration. Staging and installation never change root instructions, the session's default agent, or global Codex configuration. Export local Codex model/reasoning settings before syncing. Neither sync dry-run/check nor lifecycle doctor writes files.

`oc sync all` renders both adapters deterministically. `oc sync opencode` is raw generation only; retain `just config` or the existing launch workflow for OpenCode's memory/reliability postprocessing. Do not interpret a raw adapter drift check as verification of postprocessed OpenCode configuration.

Every meaningful task should be recoverable from Git rather than depending on chat history.

Recommended flow:

```text
1. durable requirement/design in docs or issue
2. task branch
3. implementation
4. tests/checks
5. PR
6. review
7. merge
8. memory candidate for durable contextual facts, when useful
```

A runtime handoff therefore points to repository artifacts:

```text
Read AGENTS.md.
Read docs/en/MULTI_RUNTIME.md.
Read docs/en/CODEX_ADAPTER.md.
Implement the next unchecked milestone on a dedicated branch.
Preserve current OpenCode behavior.
Run the relevant tests and prepare a PR.
```

This is better than pasting a large conversation into a new runtime.

## Handoff contract between runtimes

When stopping work in one runtime and continuing in another, leave a concise handoff in the branch/PR description or a task document containing:

```text
GOAL
CURRENT STATE
FILES CHANGED
DECISIONS MADE
UNRESOLVED QUESTIONS
TESTS RUN
KNOWN FAILURES
NEXT SAFE STEP
```

Do not store chain-of-thought. Store decisions, evidence, implementation state, and next actions.

## Parallel work

OpenCode, Codex, and GitHub-connected assistants may work in parallel only when their write scopes do not overlap.

Good split:

```text
Codex branch A      -> runtime/common refactor
ChatGPT branch B    -> documentation/ADR
OpenCode branch C   -> V2 watchdog regression fix
```

Risky split:

```text
Codex and OpenCode both modify scripts/generate-config on separate long-lived branches
```

Prefer short branches and rebase/update before touching a shared hotspot.

## Documentation-driven implementation

For architectural work, documentation should become the stable contract before runtime-specific implementation diverges.

Recommended sequence:

```text
design discussion
   -> docs PR
   -> review/merge
   -> implementation PR(s)
```

The docs PR should define:

- ownership boundaries;
- source of truth;
- public CLI/API contract;
- invariants;
- migration sequence;
- acceptance criteria;
- known runtime limitations.

This lets Codex, OpenCode, or another assistant implement the same target independently.

## Model strategy across runtimes

Keep task policy stable while model names vary.

Example portable intent:

```text
research/exploration       low
implementation             medium
orchestration              high
independent final review   high
```

Each runtime resolves these tiers independently.

Do not copy a Codex-specific model slug into `agents/<name>/agent.json` simply because one implementation session used it successfully.

## Memory workflow across runtimes

Codex can retrieve context and propose candidates through the manually registered local MCP service. Local Codex sync does not render context, access a private vault, check service availability, or propose candidates. Follow the [PR5 MCP setup](CODEX_ADAPTER.md#memory-integration--pr5) and explicitly synchronize the plugin/vault before launching MCP.

### Reading memory

Every runtime should receive the same bounded, project-scoped rendered context from `opencode-memory-plugin` where integration exists.

The runtime should not mount the private memory vault merely to read context.

### Proposing memory

After a meaningful task, a runtime may propose durable facts such as:

- an architectural decision;
- a stable repository convention;
- an important project constraint;
- a changed ownership boundary;
- a reusable workstyle preference.

A proposal is not durable memory yet.

```text
runtime -> candidate quarantine -> human accept -> human promote -> explicit push
```

### What should not become memory

Do not propose:

- transient build failures already represented by an issue;
- raw command output;
- large diffs;
- secrets;
- speculative conclusions;
- temporary branch state;
- information already obvious from canonical repository files.

## Suggested implementation split

The multi-runtime migration is intentionally decomposable so different runtimes can implement different PRs.

### PR 1 — documentation and contracts

- multi-runtime architecture;
- Codex adapter contract;
- cross-runtime workflow;
- documentation index updates.

### PR 2 — common normalization

- extract normalized agent representation;
- snapshot/golden tests for OpenCode output;
- no Codex behavior required yet.

### PR 3 — adapter interface + OpenCode migration

- common adapter interface;
- existing OpenCode compiler consumes normalization;
- prove no functional regression.

### PR 4 — local Codex adapter (implemented)

- generated Codex instructions;
- local model/reasoning mapping;
- `oc sync codex`;
- dry-run/check/idempotence tests.

Native agent TOML and instruction files are staged in `.generated/codex/`; opt-in installation remains manual. Fine-grained permission and graph allowlist intent is documented rather than claimed as full OpenCode enforcement parity.

### PR 5 — portable memory surface (implemented)

[Memory-plugin PR #10](https://github.com/ylascaux/opencode-memory-plugin/pull/10) owns the shared portable API and five-tool stdio MCP adapter. The toolkit pins the tested dependency, offers a local prebuilt-service launcher, and documents manual Codex registration. Generated Codex instructions describe support without claiming availability. Native OpenCode capture and human CLI lifecycle remain intact.

Validation includes full memory tests, toolkit checks, official SDK stdio smoke on a synthetic Git vault, and V1/V2 native capture fixtures. No private memory is copied into generated artifacts and no automatic acceptance, promotion, or push is implemented.

### PR 6 — optional remote OpenAI resources

- explicit Agent API sync;
- explicit Skills publication/versioning;
- ownership metadata;
- remote dry-run;
- safe deletion policy.

PR 6 remains optional and does not block local Codex or portable memory support.

## Prompt for Codex

Once the documentation PR is merged, a minimal implementation prompt should be enough:

```text
Read AGENTS.md and the multi-runtime documentation:
- docs/en/MULTI_RUNTIME.md
- docs/en/CODEX_ADAPTER.md
- docs/en/CROSS_RUNTIME_WORKFLOW.md

Inspect the current implementation before editing.
Implement only the next migration milestone, preserving OpenCode behavior.
Use the documented source-of-truth and compatibility rules.
Run relevant tests and prepare a PR with a clear handoff.
```

For a specific milestone, append for example:

```text
Implement PR 2: common normalization only. Do not add Codex generation yet.
```

## Prompt for a GitHub-connected assistant

```text
Read the multi-runtime documentation and inspect the current repository state.
Review the implementation PR for conformance with the documented source-of-truth,
compatibility, idempotence, memory boundary, and runtime portability requirements.
Leave concrete findings or prepare a follow-up PR for documentation/test gaps.
```

## Completion rule

A task is complete when another runtime can understand what changed from Git/PR artifacts alone.

Chat history may help a human, but it must never be required to reconstruct the project's engineering state.
