# Agents

The toolkit currently defines 40 agents. Each agent is a self-contained component under `agents/<name>/`.

For the complete configuration format, see [AGENT_CONFIGURATION.md](./AGENT_CONFIGURATION.md).

## Directory layout

```text
agents/<name>/
├── agent.json
├── prompt.md
└── permissions.json
```

Shared defaults live under:

```text
agents/_defaults/
├── agent.json
├── prompt.md
└── permissions.json
```

The runtime config is generated; do not edit `.generated/`, `opencode.jsonc`, or `opencode.v2.jsonc` as source files.

## Responsibilities

`meta-router` is the primary control-plane agent. It classifies each request and routes to the minimum sufficient lead or specialist.

The normal hierarchy remains deliberately shallow:

```text
meta-router
  -> lead/orchestrator
      -> leaf specialist
```

The maximum delegation depth is two.

Topology is declared by the child through `agent.json.parents`. This lets a new agent join one or more leads without modifying a central map.

## Common lead agents

- `orchestrator`: delivery, fixes, migrations, incidents, and structured external research workflows
- `review-lead`: independent review
- `platform-architect`: platform-wide architecture
- `security-lead`: defense-in-depth security assessment

Escalation/evidence specialists such as `arbiter`, `deep-reasoner`, and `evidence-auditor` can be reachable from several leads.

The generic structured-research leaves are:

- `source-discovery`: LOW-cost candidate source discovery; never certifies domain facts
- `structured-extractor`: MEDIUM structured extraction from supplied evidence and caller-owned schemas
- `entity-resolver`: MEDIUM identity resolution without mutating canonical records

See [RESEARCH_PIPELINE.md](./RESEARCH_PIPELINE.md) for their external orchestration boundary and escalation policy.

## Add an agent

```bash
just new-agent cloudflare --parent platform-architect --tier medium --model-profile reasoning
```

Then edit the generated directory and validate with:

```bash
just config
just check
```

`just agents` shows the discovered catalog, models, parents and children.
