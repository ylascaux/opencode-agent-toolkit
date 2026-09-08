# OpenCode Agent Toolkit

A configurable multi-agent toolkit for OpenCode, focused on software engineering, platform engineering, AWS, Terraform/Terragrunt, Python, Go, testing, architecture discovery and technical design.

## What is included

- `orchestrator`: primary agent that delegates to specialists.
- `brainstorm`: explores competing approaches and trade-offs.
- `planner`: turns requirements into implementation plans.
- `builder`: general multi-file implementation agent.
- `reviewer`: read-only code review.
- `tester`: unit, integration and end-to-end tests.
- `mock-generator`: mocks, fakes, fixtures and test builders.
- `debugger`: evidence-first root-cause investigation.
- `project-scanner`: inspects repositories under `Projects/` or normalized inventory JSON.
- `architecture-designer`: produces target architectures, ADR-style decisions and Mermaid diagrams.
- `terraform-terragrunt`: Terraform/OpenTofu/Terragrunt specialist with destructive actions denied by default.
- `python-specialist`: typed, testable Python services and automation.
- `go-specialist`: Go services, CLIs, concurrency and AWS integrations.
- `aws-platform`: AWS platform architecture specialist.
- `security-reviewer`: application, IaC and cloud security review.
- `docs-writer`: README, ADR and runbook authoring.

Each agent has an independently configurable model through environment variables.

## Model mapping

Copy the example file and customize the models exposed by your OpenCode provider/LiteLLM gateway:

```bash
cp .env.example .env
```

Example:

```dotenv
MODEL_ORCHESTRATOR=litellm/gpt-5.6-sol
MODEL_BRAINSTORM=litellm/gpt-5.6-luna
MODEL_BUILDER=litellm/claude-sonnet-5
MODEL_ARCHITECTURE=litellm/gpt-5.6-sol
MODEL_TERRAFORM=litellm/claude-sonnet-5
MODEL_PYTHON=litellm/claude-sonnet-5
MODEL_GO=litellm/claude-sonnet-5
MODEL_AWS=litellm/gpt-5.6-sol
```

`opencode.jsonc` references them with OpenCode environment substitution, for example:

```jsonc
"terraform-terragrunt": {
  "model": "{env:MODEL_TERRAFORM}"
}
```

## Architecture discovery

### Direct agent mode

Ask the scanner to inspect your local projects:

```text
@project-scanner Analyse les projets présents dans ~/Projects et génère un inventaire d'architecture.
```

External-directory access remains permission-gated by OpenCode.

### JSON inventory mode

The bundled Python scanner can normalize project metadata before passing it to the architecture agent:

```bash
./scripts/scan-projects > architecture-inventory.json
```

Then ask:

```text
@architecture-designer Analyse architecture-inventory.json et propose une architecture cible.
```

### Local inventory API

Install dependencies:

```bash
make setup
```

Start the API:

```bash
./scripts/inventory-api
```

Then:

```bash
curl -sS -X POST http://127.0.0.1:8765/scan \
  -H 'content-type: application/json' \
  -d '{}' > architecture-inventory.json
```

The API is constrained to `PROJECTS_ROOT` (default: `$HOME/Projects`).

## Terraform safety

The Terraform/Terragrunt agent is intentionally conservative:

- formatting and validation can be allowed;
- plans require approval;
- `apply` and `destroy` are denied by default.

This repository is a starting point: tune command permissions to your environment before using it against production infrastructure.

## Typical workflow

```text
orchestrator
├── brainstorm
├── planner
├── builder / python-specialist / go-specialist / terraform-terragrunt
├── tester
├── reviewer
└── security-reviewer
```

Architecture workflow:

```text
Projects/*
   ↓
project-scanner
   ↓
architecture-inventory.json
   ↓
architecture-designer
   ├── aws-platform
   └── terraform-terragrunt
```

## Development

Run scanner tests with:

```bash
python -m unittest discover -s tests -v
```

## License

MIT.
