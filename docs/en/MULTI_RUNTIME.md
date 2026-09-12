# Multi-runtime architecture

## Goal

`opencode-agent-toolkit` should evolve from an OpenCode-specific toolkit into a **runtime-neutral agent control plane**.

The toolkit remains the source of truth for agent roles, prompts, permissions, model quality tiers, delegation topology, reliability intent, and memory integration. Runtime adapters compile that source into artifacts understood by OpenCode, Codex, and future runtimes.

```text
                         opencode-agent-toolkit
                         SOURCE OF TRUTH
                                 |
                 +---------------+---------------+
                 |                               |
                 v                               v
          OpenCode adapter                  Codex adapter
                 |                               |
                 v                               v
        OpenCode generated config        Codex generated artifacts

                                 |
                                 v
                     opencode-memory-plugin
                                 |
                                 v
                       private memory vault
```

The synchronization direction is deliberately one-way:

```text
Toolkit -> runtime artifacts
```

Runtime-specific files must never become an independent editable source of truth.

## Implemented now

One normalized graph from `runtime/common/normalization.py` feeds the common `RuntimeAdapter` boundary and the `OpenCodeAdapter` / local `CodexAdapter`. Shared artifact planning supports deterministic writes, dry-run, and drift checks. OpenCode keeps its existing generated paths and golden output; Codex stages a separate bundle under `.generated/codex/`.

```bash
oc sync codex
oc sync codex --dry-run
oc sync codex --check
oc sync codex --verbose
oc sync opencode
oc sync all
```

Sync is local and does not launch a model, load `.env` / `.env.local`, or contact providers. Use exported `CODEX_MODEL_*` / `CODEX_REASONING_*` settings for Codex. `opencode` sync is the raw `scripts/generate-config` stage: `just config` and the existing launch workflow still apply memory/reliability configuration, including V2 plugin-directory handling. A raw OpenCode check after those postprocessors can report drift; it compares raw adapter output, not effective postprocessed configuration.

Codex's generated native agent TOML requires manual opt-in installation; the root `AGENTS.md` is untouched, and `runtime.json` is toolkit metadata, not native configuration. See [Codex local use and limitations](CODEX_ADAPTER.md#implemented-local-workflow).

Memory/MCP integration for Codex, remote Agents/Skills publication, and bidirectional sync are **not implemented**. No portable canonical skill files are currently tracked, so local skill packaging is deferred and reported as zero mapped skills. Memory diagrams and expanded capabilities below describe the longer-term target, not current Codex behavior.

## Existing sources of truth

The current repository already contains the right primitives for this design:

- `agents/<name>/agent.json`: runtime-neutral agent metadata plus optional runtime-specific extensions;
- `agents/<name>/prompt.md`: agent behavior;
- `agents/<name>/permissions.json`: agent permission overrides;
- `agents/_defaults/`: inherited defaults;
- quality tiers (`low`, `medium`, `high`) instead of hard-coded provider models;
- deterministic generation and validation;
- a shallow parent/child graph;
- external memory through `opencode-memory-plugin`.

The multi-runtime work should **extract and formalize these primitives**, not replace them with another manifest.

## Design principles

### 1. Runtime-neutral first

An agent definition describes intent:

```json
{
  "description": "Inspect a repository and return evidence-backed findings.",
  "mode": "subagent",
  "tier": "low",
  "steps": 10,
  "parents": ["orchestrator"]
}
```

It must not require an OpenCode or OpenAI model slug.

Runtime-specific configuration belongs below a namespaced extension when unavoidable:

```json
{
  "opencode": {},
  "codex": {}
}
```

Common behavior must stay outside those extensions.

### 2. Capability tiers stay stable

The portable contract is:

```text
low
medium
high
```

Concrete model selection happens in the runtime adapter or local profile.

Example only:

```text
                    OpenCode profile       Codex profile
low                 inexpensive model      fast/cheap coding model
medium              balanced model         balanced coding model
high                strongest model        strongest coding model
```

Model names change faster than the agent graph. They must therefore remain configuration, not architecture.

### 3. Reliability semantics are portable, implementations are not

The toolkit owns the intent:

- maximum delegation depth;
- maximum parallel children;
- bounded retries;
- step/task budgets;
- stall handling;
- no destructive Git behavior by default;
- independent review where required;
- producer must not certify its own work;
- completed handoffs should be reused rather than recomputed.

Each runtime adapter may implement those semantics differently depending on its native APIs.

If a runtime cannot enforce a guard deterministically, the adapter must expose that limitation instead of pretending the guard exists.

### 4. Memory is a service boundary

Memory does not belong to either runtime.

```text
OpenCode ----+
             |
Codex -------+---- opencode-memory-plugin ---- private Git memory vault
             |
other -------+
```

The toolkit configures access. Capture, candidate extraction, curation, retrieval, Git persistence, and promotion remain owned by `opencode-memory-plugin`.

The long-term portable interface should expose operations equivalent to:

```text
memory.search
memory.render
memory.propose
memory.list_candidates
memory.accept
memory.promote
```

Agents may propose candidates. Durable promotion remains explicit and reviewable.

### 5. Generated artifacts are disposable

Runtime artifacts should be reproducible from the toolkit sources.

A clean checkout plus local runtime profile should be enough to regenerate them.

Generated outputs should carry a header such as:

```text
GENERATED FILE - DO NOT EDIT
Source: opencode-agent-toolkit
Regenerate with: oc sync <runtime>
```

## Target repository architecture

The exact implementation may evolve, but the logical split should look like:

```text
agents/                         # canonical agent sources
contracts/                      # portable handoff/routing schemas
runtime/
  common/                       # normalized model and validation
  opencode/                     # OpenCode compiler/adapter
  codex/                        # Codex compiler/adapter
scripts/
  ...
.generated/
  opencode/
  codex/
```

Do not move files simply to match this diagram if the current code can achieve the same boundary with less churn.

## Normalized agent model

The common compiler should normalize every agent into one internal representation before invoking an adapter.

Conceptual shape:

```yaml
name: repo-researcher
description: Inspect repository evidence
mode: subagent
parents:
  - orchestrator
model:
  tier: low
  override_env: MODEL_REPO_RESEARCHER
reasoning:
  tier: low
permissions:
  read: allow
  edit: deny
  shell: ask
  delegate: deny
memory:
  read: true
  propose: true
reliability:
  steps: 10
```

This is an internal contract, not necessarily a new user-facing YAML format.

## Synchronization CLI

Implemented UX:

```bash
oc sync opencode
oc sync codex
oc sync all
```

Useful options:

```bash
oc sync codex --dry-run
oc sync codex --check
oc sync codex --verbose
```

`--verbose` includes resolved model policy and capability limitations; dry-run includes these details automatically.

Semantics:

- `--dry-run`: render and diff without writing;
- `--check`: exit non-zero if generated artifacts are stale;
- default: update generated runtime artifacts idempotently;
- two identical runs must produce byte-identical output.

Illustrative future dry-run summary (not the current skills/memory capability claim):

```text
Codex synchronization

agents:          41 discovered
skills:          6 mapped
memory:          configured
AGENTS.md:       update required
runtime config:  update required

model policy:
  orchestrator   high
  implementer    medium
  researcher     low
  reviewer       high
```

Counts are discovered dynamically; they must not be hard-coded.

## Configuration precedence

Portable intent should resolve before runtime configuration:

```text
agent-local override
        -> tier/profile mapping
        -> runtime-specific local override
        -> runtime default
```

Secrets and personal model preferences must remain outside committed generated files.

For implemented Codex mapping, exported per-agent overrides win over optional Codex extension values, then exported tier settings, then local runtime defaults (or the canonical tier for reasoning). Exact variable names and supported extension keys are documented in [Codex model tiers](CODEX_ADAPTER.md#model-tiers).

## Compatibility strategy

Migration must be incremental:

1. preserve existing OpenCode behavior;
2. extract a normalized internal representation from the existing generator;
3. make the existing OpenCode generation consume that normalized representation;
4. prove no behavior regression with tests;
5. add Codex generation from the same representation;
6. only then simplify duplicated legacy paths.

A large rewrite that implements Codex first and reconstructs OpenCode later is explicitly out of scope.

## Testing requirements

At minimum, multi-runtime support must test:

- discovery and normalization of every agent;
- graph validation;
- portable model tier resolution;
- OpenCode adapter output;
- Codex adapter output;
- adapter-specific overrides without leaking into the other adapter;
- dry-run does not modify files;
- check mode detects stale artifacts;
- idempotent generation;
- stable ordering;
- memory integration rendering when that future Codex milestone is implemented;
- invalid runtime configuration fails before launching a model;
- generated files cannot silently become source inputs.

Golden/snapshot tests are appropriate for deterministic generated artifacts.

## Non-goals

Initial multi-runtime support does not require:

- feature parity for every low-level OpenCode plugin hook;
- moving memory implementation back into this repository;
- hiding differences between runtimes;
- automatic promotion of memory candidates;
- hard-coding current Codex model names into agent definitions;
- publishing remote OpenAI resources during ordinary local config generation.

## Definition of done

The full multi-runtime roadmap is considered established when (items 5 and broader skill support remain future work):

1. existing OpenCode workflows still pass unchanged;
2. a single normalized agent graph feeds both OpenCode and Codex adapters;
3. `oc sync codex --dry-run` explains what would be generated;
4. Codex can consume the generated instructions/skills/configuration without duplicating source definitions;
5. memory context can be rendered for Codex without exposing the private vault to the runtime;
6. documentation clearly states which reliability guarantees are deterministic for each runtime.
