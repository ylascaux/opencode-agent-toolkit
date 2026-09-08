# Model strategy

Every agent keeps its own `MODEL_*` variable, but model selection should be managed by capability profiles rather than by manually choosing 37 unrelated values.

## Profiles

| Profile | Typical roles | Goal |
|---|---|---|
| `fast` | brainstorm, scanner, mocks, secrets, docs | low latency/cost for bounded tasks |
| `general` | meta-router, planner, observability, FinOps | strong everyday reasoning |
| `coding` | builder, tester, Python, Go, Terraform, CI/CD | reliable implementation/tool use |
| `reasoning` | orchestrator, debugger, AWS, Kubernetes, database, networking, threat-model | harder technical decisions |
| `deep` | platform-architect, deep-reasoner | high-complexity/irreversible decisions |
| `review` | review-lead, reviewer, evidence-auditor, API contract, supply-chain | independent critical review |
| `security` | security-lead, AppSec, IaC security, pentest | security-focused analysis/validation |

Run `just configure` to discover `/v1/models`, get heuristic profile recommendations and map the selected profiles across all 37 agents.

## Independence

When possible, use a different model family for implementation and independent review/security. This reduces correlated blind spots. Do not force diversity when the alternative model is materially less capable for the task.

## Escalation economics

The system is designed so expensive/deep models are not used by default. Low-risk bounded work should stay on fast/general/coding profiles. High risk, irreversible decisions, material disagreement or low confidence justify escalation to reasoning/deep profiles.

## Gateway credentials

`just configure` may read `LITELLM_API_KEY`, `CF_ACCESS_TOKEN` and `LITELLM_HEADERS_JSON` from the process environment for discovery. It writes model mappings only; credentials are not persisted by the configurator.
