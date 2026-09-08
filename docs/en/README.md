# Documentation

The toolkit is a 37-agent engineering system with a shallow, auditable control plane.

## Read in this order

1. [Toolkit system architecture](SYSTEM_ARCHITECTURE.md) — **start here to understand the whole system**
2. [Installation](INSTALLATION.md)
3. [Agent architecture](AGENTS.md)
4. [Routing](ROUTING.md)
5. [Model strategy](MODEL_STRATEGY.md)
6. [Reliability and guardrails](RELIABILITY.md)
7. [Usage](USAGE.md)
8. [Security](SECURITY.md)
9. [Architecture workflow produced by the agents](ARCHITECTURE.md)
10. [Project discovery](PROJECT_DISCOVERY.md)
11. [OpenCode compatibility](OPENCODE_COMPATIBILITY.md)

`SYSTEM_ARCHITECTURE.md` describes the toolkit itself: `oc` boot flow, config generation, control plane, delegation, model resolution, watchdog, subagent queue, failure modes and extension points. `ARCHITECTURE.md` instead describes the workflow used to design and review a target project's architecture.

The two machine-readable contracts are in `contracts/`:
- `agent-handoff.schema.json`
- `routing-decision.schema.json`
