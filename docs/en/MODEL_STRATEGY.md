# Model strategy

The toolkit is provider-agnostic. Agent definitions do not hard-code GitHub Copilot, OpenAI, Codex, LiteLLM or any other provider.

## Three capability tiers

Every agent is assigned to one of three stable capability tiers in `profiles/agent-tiers.json`:

| Tier | Default Copilot model | Typical use |
|---|---|---|
| `low` | `github-copilot/gpt-5.6-luna` | tightly bounded, low-risk mechanical tasks |
| `medium` | `github-copilot/gpt-5.6-terra` | normal engineering, evidence gathering, documentation and operational analysis |
| `high` | `github-copilot/gpt-5.6-sol` | architecture, security, arbitration and deep reasoning |

The default mapping is quality-focused rather than aggressively cost-minimized. Only `mock-generator` and `secrets` are LOW by default. Tasks that become inputs to later decisions, such as repository architecture discovery, durable documentation, observability analysis, FinOps analysis, evidence auditing and brainstorming, use at least MEDIUM.

Examples:

- `mock-generator` -> LOW
- `secrets` -> LOW
- `project-scanner` -> MEDIUM
- `docs-writer` -> MEDIUM
- `builder` -> MEDIUM
- `evidence-auditor` -> MEDIUM
- `platform-architect` -> HIGH
- `appsec` -> HIGH

The agent-to-tier mapping is independent from the concrete provider model. An agent keeps the same capability tier when switching from Copilot to another provider profile.

## Why evidence-producing agents are not LOW

Some apparently simple agents create inputs that other agents treat as evidence. A weak result there can propagate into otherwise high-quality downstream reasoning.

For example, `project-scanner` discovers components, interfaces, infrastructure, data stores and evidence relationships used by architecture agents. `docs-writer` preserves decisions, assumptions, migration and rollback details in durable artifacts. `observability` and `finops` make operational trade-offs rather than merely extract values. These are MEDIUM by default.

`evidence-auditor` is MEDIUM because its normal work is structured verification. Material disagreement or unresolved high-risk uncertainty should escalate to HIGH agents such as `arbiter` or `deep-reasoner` instead of making every audit HIGH by default.

## Profiles

Concrete model choices live in `profiles/*.env.example`.

```bash
just profiles
just profile copilot
just profile codex
just models
```

The default work profile is `copilot`.

OpenCode's GitHub Copilot provider is `github-copilot`. Check the models available to your account before relying on a profile unchanged:

```bash
opencode models github-copilot
```

If your subscription exposes different IDs, edit `profiles/copilot.env.example`; no agent or routing definition needs to change.

## Personal / Codex usage

`profiles/codex.env.example` is a ready-to-edit personal profile. It intentionally separates the provider choice from the toolkit architecture.

```bash
just profile codex
```

You may use one model for all three tiers or assign different Codex/OpenAI models to `MODEL_LOW`, `MODEL_MEDIUM` and `MODEL_HIGH`.

## Per-agent overrides

Persistent overrides belong in `.env.local`:

```bash
MODEL_BUILDER=openai/gpt-5.3-codex
MODEL_REVIEWER=github-copilot/gpt-5.6-sol
```

`.env.local` is sourced after `.env` and profile switching never modifies it.

Resolution order:

```text
MODEL_<AGENT> override
        ↓
agent tier from profiles/agent-tiers.json
        ↓
MODEL_LOW / MODEL_MEDIUM / MODEL_HIGH from active profile
```

## Why tiers instead of 37 fixed models?

Tiers keep cost/quality policy stable while providers evolve. You can change three model values and immediately migrate all 37 agents without editing generated OpenCode configs or the agent manifest.

`meta-router` routes ordinary work toward medium paths and uses high-tier control agents for high-risk, low-confidence, security-sensitive or architecture-heavy work. LOW is intentionally reserved for narrow tasks where mistakes have limited downstream impact.

## LiteLLM

LiteLLM is optional and not part of the default setup. `just configure-litellm` remains available for future gateway-based discovery. Credentials used for discovery are not persisted by the configurator.
