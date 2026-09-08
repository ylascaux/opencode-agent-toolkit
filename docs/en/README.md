# OpenCode Agent Toolkit — English guide

This toolkit turns OpenCode into a cost-aware, evidence-driven multi-agent engineering system for software delivery, platform engineering, AWS, Terraform/Terragrunt, Python, Go, reliability and security.

## Core idea

The default control plane is `meta-router`. It classifies each task by domain, complexity, risk, uncertainty and blast radius, then chooses the minimum sufficient route. Simple work stays cheap. Complex or risky work escalates to the orchestrator and specialist councils.

```text
User
  |
  v
meta-router
  |-- simple task --------------------> narrow specialist
  |-- implementation ----------------> orchestrator -> build/test/review/security
  |-- architecture ------------------> architecture council
  |-- disagreement ------------------> arbiter
  |-- high risk / low confidence ----> deep-reasoner
  `-- completion proof --------------> evidence-auditor
```

## Main capabilities

- 35 independently configurable agents.
- Per-agent `MODEL_*` mapping for LiteLLM/Smart Router or any compatible provider.
- Adaptive routing instead of calling every agent on every task.
- Independent correctness, security and evidence reviews.
- AWS/platform architecture council.
- Terraform/Terragrunt safety controls.
- Authorized, scoped and non-destructive pentest validation.
- Read-only multi-repository architecture discovery under `PROJECTS_ROOT`.
- OpenCode V1 stable and OpenCode 2 beta compatibility.
- One-command setup through `just install`.

## Start here

1. [Installation](INSTALLATION.md)
2. [Usage](USAGE.md)
3. [Routing and model strategy](ROUTING.md)
4. [Architecture](ARCHITECTURE.md)
5. [Agents](AGENTS.md)
6. [Security](SECURITY.md)
7. [Project discovery](PROJECT_DISCOVERY.md)
8. [OpenCode compatibility](OPENCODE_COMPATIBILITY.md)
