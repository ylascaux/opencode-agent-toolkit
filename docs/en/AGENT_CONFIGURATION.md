# Agent configuration

Each agent is a self-contained component under `agents/<name>/`.

```text
agents/
├── _defaults/
│   ├── agent.json
│   ├── prompt.md
│   └── permissions.json
├── meta-router/
│   ├── agent.json
│   ├── prompt.md
│   └── permissions.json
└── ...
```

## Source of truth

The editable source of truth is the agent directory itself. There is no central editable manifest, permission catalog, or model-tier catalog.

- `agent.json`: catalog description, OpenCode mode, model environment variable, quality tier, optional LiteLLM profile hint, step budget, parents, and optional OpenCode-specific settings.
- `prompt.md`: behavior specific to this agent.
- `permissions.json`: only permission overrides specific to this agent.
- `agents/_defaults/*`: common values inherited by every agent.

`just config` discovers all agent directories, validates the graph, merges defaults, and writes generated runtime artifacts under `.generated/` plus `opencode.jsonc` / `opencode.v2.jsonc`.

## Example

```json
{
  "description": "Use for Cloudflare architecture and migration analysis.",
  "mode": "subagent",
  "model_env": "MODEL_CLOUDFLARE",
  "tier": "medium",
  "model_profile": "reasoning",
  "steps": 16,
  "parents": ["platform-architect"],
  "opencode": {}
}
```

`parents` is intentionally declared by the child. Adding an agent therefore does not require editing a central `LEAD_CHILDREN` map or changing the parent's file.

## Prompt composition

The final runtime prompt is composed from:

1. `# Role` generated from `agent.json.description`
2. `agents/<name>/prompt.md`
3. `agents/_defaults/prompt.md`
4. deterministic reliability supervision appended to agents that can delegate children

Generated prompts live under `.generated/prompts/` and must not be edited directly.

## Permissions

`agents/_defaults/permissions.json` is the baseline. The agent-local `permissions.json` recursively overrides it.

The default policy is intentionally usable:

- `websearch`: allow
- `webfetch`: allow
- safe repository/shell reads: allow
- unknown non-destructive shell operations: ask
- sensitive reads: ask
- edits: ask unless the agent explicitly allows them
- clearly destructive operations: deny

Delegation (`task` / `subagent`) is not configurable through `permissions.json`; it is derived from the `parents` graph so topology and permissions cannot drift apart.

## Models

`tier` is one of `low`, `medium`, or `high` and maps to `MODEL_LOW`, `MODEL_MEDIUM`, or `MODEL_HIGH`.

`model_env` is the optional per-agent override variable, for example `MODEL_CLOUDFLARE`. If that variable is unset, the selected tier model is used.

`model_profile` is only a hint for the optional LiteLLM discovery workflow. It does not make LiteLLM mandatory.

`just config` never contacts LiteLLM and never prompts for provider configuration. LiteLLM discovery is explicit:

```bash
just configure-litellm
```

## Add an agent

```bash
just new-agent cloudflare --parent platform-architect --tier medium --model-profile reasoning
```

Then edit:

```text
agents/cloudflare/agent.json
agents/cloudflare/prompt.md
agents/cloudflare/permissions.json
```

and validate:

```bash
just config
just check
```

## Validation

Configuration generation fails before OpenCode starts for invalid JSON, missing files, unknown parents, cycles, any delegation path deeper than two levels, duplicate model environment variables, invalid tiers/profiles, invalid permission effects, or attempts to define delegation topology inside `permissions.json`.
