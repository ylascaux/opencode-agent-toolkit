# Routing

The router optimizes for the **cheapest sufficient path**, not the fewest agents at any cost.

## Decision dimensions

Before delegation, `meta-router` classifies domain(s), complexity, risk, uncertainty, blast radius and change type. The machine-readable shape is `contracts/routing-decision.schema.json`.

## Top-level routes

```text
implementation / fix / incident -> orchestrator
review                         -> review-lead
architecture / platform / cost -> platform-architect
security assessment            -> security-lead
material disagreement          -> arbiter
high-risk low-confidence       -> deep-reasoner
weak completion evidence       -> evidence-auditor
```

## Delegation depth

```text
meta-router -> lead/orchestrator -> leaf
```

Leads never call other leads. Leaf agents cannot call any subagent. This keeps `subagent_depth=2` sufficient.

## Review routing

`review-lead` starts from the changed surface and invokes only relevant dimensions. Examples: pure Go logic -> baseline reviewer; public HTTP contract -> reviewer + API contract + relevant AppSec; SQL migration -> reviewer + database; ingress/WAF/IAM Terraform -> reviewer + networking + IaC security.

## Escalation

Use `arbiter` only for material conflicts between credible findings. Use `deep-reasoner` for costly/irreversible decisions, high/critical risk, incomplete evidence or persistent low confidence. Use `evidence-auditor` when important conclusions depend on claims such as “tests pass”, “the plan is safe”, or “the runtime finding is fixed”.
