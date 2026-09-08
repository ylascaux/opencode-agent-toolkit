# OpenCode Agent Toolkit — Platform Engineering Edition

A cost-aware, evidence-driven multi-agent engineering system for OpenCode, focused on software delivery, AWS/platform architecture, Terraform/Terragrunt, Python, Go, reliability and defense-in-depth security.

## What makes it different

- **35 independently configurable agents**.
- A **meta-router** chooses the minimum sufficient agent path instead of invoking everything.
- An `orchestrator` handles complex multi-step work.
- `arbiter`, `deep-reasoner` and `evidence-auditor` provide disagreement resolution, escalation and proof verification.
- Architecture council: repository scanner + platform architect + AWS + Kubernetes + Terraform + networking + database + SRE + observability + FinOps.
- Security pipeline: threat model + AppSec + IaC security + supply chain + secrets + authorized non-destructive pentest.
- Every agent maps to its own `MODEL_*` environment variable.
- Native configs for **OpenCode V1 stable** and **OpenCode 2 beta** generated from one source of truth.
- Multi-repository discovery under `~/Projects` plus JSON CLI/API inventory.

## Quick start

```bash
brew install just
git clone https://github.com/ylascaux/opencode-agent-toolkit.git
cd opencode-agent-toolkit
just install
just doctor
just run
```

The installer creates `.env` from `.env.example` only when needed, preserves your existing model mapping, creates the Python environment, generates both OpenCode configs, validates them and runs tests.

## Daily command surface

```bash
just                 # list recipes
just install         # first-time setup
just doctor          # environment/config health check
just run             # launch selected OpenCode runtime
just v1              # force OpenCode V1 stable
just v2              # force OpenCode 2 beta
just check           # regenerate configs + validate + tests
just test            # repository tests
just scan            # create architecture-inventory.json
just api             # run the local project inventory API
just models          # show MODEL_* mappings
just refresh         # rebuild Python environment
just clean           # remove generated local state
```

## OpenCode commands

```text
/auto <task>          adaptive general routing
/ship <feature/fix>   implementation + verification gates
/review <change>      independent adaptive review
/architecture <need>  architecture council
/security <scope>     defense-in-depth security review
/debug <problem>      evidence-first debugging
/incident <incident>  SRE/observability incident workflow
/cost <scope>         FinOps + cost/performance analysis
```

## High-level architecture

```text
                        +--> narrow specialist (simple work)
                        |
User -> meta-router ----+--> orchestrator -> plan/build/test/review/security
        |               |
        |               +--> architecture council
        |
        +--> arbiter             (material disagreement)
        +--> deep-reasoner       (high risk / low confidence)
        `--> evidence-auditor    (proof of completion)
```

## Documentation

Full bilingual documentation is under [`docs/`](docs/README.md):

- English: [`docs/en/`](docs/en/README.md)
- Français: [`docs/fr/`](docs/fr/README.md)

## Safety defaults

- Terraform/OpenTofu/Terragrunt `apply` and `destroy` are denied.
- Multi-repository project discovery is read-only.
- Security agents do not read common secret/key files by default.
- Pentesting is limited to explicitly authorized, scoped and non-destructive validation.
- High-risk or low-confidence work escalates instead of being silently accepted.

## Validate

```bash
just check
```

## License

MIT.
