# OpenCode Agent Toolkit — Platform Engineering Edition

A multi-agent engineering system for OpenCode focused on architecture, implementation, testing, AWS/platform engineering and defense-in-depth security review.

## Highlights

- 27 independently configurable agents.
- OpenCode V2 `agents` / `permissions` / `subagent` syntax.
- Architecture council: scanner + platform architect + AWS + Kubernetes + Terraform + SRE + observability + FinOps.
- Engineering loop: brainstorm → plan → build → test → review.
- Security pipeline: threat model → AppSec → IaC security → supply chain → secrets → authorized non-destructive pentest.
- Per-agent model routing through `.env` + `{env:MODEL_*}`.
- Reusable `/ship`, `/architecture`, `/security`, `/debug` commands.
- Read-only multi-repository discovery under `~/Projects` plus a JSON inventory CLI/API.

## Install

```bash
git clone https://github.com/ylascaux/opencode-agent-toolkit.git
cd opencode-agent-toolkit
cp .env.example .env
set -a && source .env && set +a
./scripts/opencode-agents
```

Customize every `MODEL_*` variable for your LiteLLM/provider model IDs.

## Entry points

```text
/ship <feature or fix>
/architecture <system or requirement>
/security <change, branch or component>
/debug <failure or incident>
```

## Architecture discovery

```bash
make setup
./scripts/scan-projects
```

This creates `architecture-inventory.json` from `$PROJECTS_ROOT` (default `$HOME/Projects`). You can also expose the same scanner locally through `./scripts/inventory-api`, then POST to `http://127.0.0.1:8765/scan`.

## Architecture council

`project-scanner → platform-architect → aws-platform / kubernetes / terraform-terragrunt / sre / observability / finops / threat-model / iac-security`

## Security pipeline

- `threat-model`: assets, trust boundaries and abuse cases.
- `appsec`: application vulnerabilities and business logic.
- `iac-security`: Terraform/Terragrunt/Kubernetes/AWS security.
- `supply-chain`: dependencies, CI, images and provenance.
- `secrets`: credential leakage detection with redacted output.
- `pentest`: scoped, authorized, non-destructive runtime validation.

The pentest agent does not persist access, exfiltrate data, perform DoS, credential spraying, lateral movement or stealth. Runtime commands require approval except harmless localhost curl checks.

## Terraform safety

Formatting and validation can run automatically; plans require approval; `apply` and `destroy` are denied.

## Model strategy

Use your strongest reasoning model for orchestration/architecture/threat modeling, strong coding models for implementation specialists, and cheaper models for scanning/mocks/docs. Prefer a different model family for independent review/security when possible.

## Validate

```bash
make check
make setup
make test
```

## License

MIT.
