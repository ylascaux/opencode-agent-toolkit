# OpenCode Agent Toolkit

A provider-agnostic multi-agent engineering toolkit for OpenCode with a shallow control plane, deterministic reliability guardrails, adaptive specialist routing, and editable per-agent configuration.

## Agent source of truth

Every agent is a self-contained component:

```text
agents/<name>/
├── agent.json
├── prompt.md
└── permissions.json
```

Shared defaults live under `agents/_defaults/`.

Adding an agent does not require editing a central manifest, permission catalog, model-tier map, or `LEAD_CHILDREN` table. The child declares its allowed parents in `agent.json`.

```bash
just new-agent cloudflare --parent platform-architect --tier medium --model-profile reasoning
just config
just check
```

`just agents` prints the discovered catalog and topology.

## Configuration

`just config` is local and deterministic:

```bash
just config
```

It discovers `agents/<name>/`, validates the graph and permissions, generates `.generated/` plus OpenCode V1/V2 configs, then applies deterministic reliability limits.

It does **not** contact LiteLLM and does not ask for provider credentials.

LiteLLM discovery is optional and explicit:

```bash
just configure-litellm
```

## Default permission philosophy

The shared default favors usability without removing hard safety boundaries:

- web search/fetch: allow
- safe repository and shell reads: allow
- unknown non-destructive commands: ask
- sensitive reads: ask
- edits: ask unless explicitly allowed by the agent
- destructive operations such as recursive delete, force-push, Terraform apply/destroy and Kubernetes delete: deny

Each agent can override the shared policy through `agents/<name>/permissions.json`.

## Reliability

The toolkit includes deterministic runtime controls for:

- bounded subagent parallelism and queueing
- progress-aware stall detection
- parent `WAITING_ON_CHILD` handling
- bounded provider retries
- bounded subagent retries
- resumable failed leaf work using OpenCode `task_id`
- step ceilings
- child/run cost ceilings when provider telemetry is available
- runtime checkpoints

A failed/cancelled leaf is retried independently; completed siblings and the parent lead are preserved.

## Model strategy

Agents declare `tier` (`low`, `medium`, `high`) and `model_env` in their own `agent.json`.

The default Copilot profile maps:

- LOW → `github-copilot/gpt-5.6-luna`
- MEDIUM → `github-copilot/gpt-5.6-terra`
- HIGH → `github-copilot/gpt-5.6-sol`

A per-agent `MODEL_*` environment variable can still override its tier model.

## Main commands

```bash
just install
just config
just check
just agents
just new-agent <name>
just models
just reliability
just doctor
just run
just configure-litellm   # optional only
```

For an `oc` command usable from any workspace:

```bash
just install-user
```

## Documentation

English: [`docs/en/`](docs/en/README.md)  
French: [`docs/fr/`](docs/fr/README.md)

Start with the toolkit architecture, then the agent configuration guide:

- [`docs/en/SYSTEM_ARCHITECTURE.md`](docs/en/SYSTEM_ARCHITECTURE.md)
- [`docs/en/AGENT_CONFIGURATION.md`](docs/en/AGENT_CONFIGURATION.md)
- [`docs/fr/SYSTEM_ARCHITECTURE.md`](docs/fr/SYSTEM_ARCHITECTURE.md)
- [`docs/fr/CONFIGURATION_AGENTS.md`](docs/fr/CONFIGURATION_AGENTS.md)
