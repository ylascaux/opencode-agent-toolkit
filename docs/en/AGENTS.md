# Agent architecture

The toolkit has **37 agents**, but they are not peers. The hierarchy is intentional.

## Control plane

| Agent | Purpose |
|---|---|
| `meta-router` | classifies work and selects one top-level path |
| `orchestrator` | multi-step delivery/incident execution |
| `review-lead` | selects independent review dimensions |
| `security-lead` | selects security gates |
| `platform-architect` | leads the architecture council |
| `arbiter` | resolves material disagreement |
| `deep-reasoner` | escalates high-risk/low-confidence decisions |
| `evidence-auditor` | verifies completion claims |

`meta-router` can invoke only the four execution/lead doors plus the three escalation/audit agents. It does not get a flat catalogue of every specialist.

## Delivery leaves

`brainstorm`, `planner`, `builder`, `tester`, `mock-generator`, `debugger`, `python-specialist`, `go-specialist`, `terraform-terragrunt`, `cicd`.

## Review leaves

`reviewer`, `api-contract`, `performance`, plus domain/security leaves selected by `review-lead`.

## Architecture/platform leaves

`project-scanner`, `architecture-designer`, `aws-platform`, `terraform-terragrunt`, `kubernetes`, `cicd`, `sre`, `observability`, `finops`, `database`, `networking`, `threat-model`, `iac-security`.

## Security leaves

`threat-model`, `appsec`, `iac-security`, `supply-chain`, `secrets`, `pentest`.

## Leaf invariant

Every leaf has an explicit deny-all `task`/`subagent` policy. Only the five routing/orchestration agents have exceptions. This prevents bypassing the control plane.

## Prompt contract

Every generated prompt contains Role, Operating method, Non-negotiables, Evidence discipline, Stop conditions and Handoff sections. Agent-specific behavior remains defined in `agents/manifest.json`.
