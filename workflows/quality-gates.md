# Quality gates

The meta-router chooses one top-level route; leads select only the leaf gates required by the actual changed surface.

## Standard code change

`meta-router -> orchestrator -> implementation specialist + tester + reviewer`

Add `evidence-auditor` for non-trivial/high-risk completion claims.

## Security-sensitive code change

`meta-router -> orchestrator -> implementation specialist + tester + relevant security leaves + reviewer`

Use `threat-model` for changed trust boundaries and `appsec` for application/auth/request surfaces. Runtime `pentest` is only for explicitly authorized targets.

## Independent review

`meta-router -> review-lead -> reviewer + only relevant API/performance/database/networking/security leaves`

## Infrastructure / architecture change

`meta-router -> platform-architect -> project-scanner (when needed) + relevant AWS/Kubernetes/Terraform/networking/database/SRE/observability/FinOps/security leaves`

## Full security assessment

`meta-router -> security-lead -> only relevant threat-model/AppSec/IaC/supply-chain/secrets/pentest leaves`

## Escalation

Material disagreement -> `arbiter`. High-risk/irreversible/low-confidence decision -> `deep-reasoner`. Weak or disputed proof -> `evidence-auditor`.

Leaf agents cannot delegate, and leads do not invoke other leads, keeping the delegation depth at two.
