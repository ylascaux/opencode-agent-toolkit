# Model strategy

The toolkit is provider-agnostic. Agent definitions do not hard-code GitHub Copilot, OpenAI, Codex, LiteLLM or any other provider.

## Three capability tiers

Every agent is assigned to one of three stable capability tiers in `profiles/agent-tiers.json`:

| Tier | Default Copilot model | Typical use |
|---|---|---|
| `low` | `github-copilot/gpt-5.6-luna` | bounded, low-risk, low-cost tasks |
| `medium` | `github-copilot/gpt-5.6-terra` | normal engineering work |
| `high` | `github-copilot/gpt-5.6-sol` | architecture, security, arbitration, deep reasoning |

The agent-to-tier mapping is independent from the concrete provider model. For example, `docs-writer` remains `low`, `builder` remains `medium`, and `platform-architect` remains `high` even when switching from Copilot to a personal Codex profile.

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

`meta-router` routes ordinary work toward low/medium paths and uses high-tier control agents for high-risk, low-confidence, security-sensitive or architecture-heavy work.

## LiteLLM

LiteLLM is optional and not part of the default setup. `just configure` and `just configure-litellm` remain available for future gateway-based discovery. Credentials used for discovery are not persisted by the configurator.
