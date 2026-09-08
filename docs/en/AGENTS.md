# Agents

The toolkit currently defines 35 independently configurable agents.

## Control plane

- `meta-router`: classifies work, chooses the cheapest sufficient route, and escalates on complexity, risk, disagreement or low confidence.
- `orchestrator`: executes multi-step workflows and coordinates specialists.
- `arbiter`: resolves material disagreements from evidence rather than majority vote.
- `deep-reasoner`: handles high-risk, ambiguous, irreversible or low-confidence decisions.
- `evidence-auditor`: checks whether completion claims are supported by actual evidence.

## General engineering

- `brainstorm`: generates materially different approaches and trade-offs.
- `planner`: converts requirements into an executable plan.
- `builder`: implements production-quality changes with minimal scope.
- `reviewer`: independent read-only correctness review.
- `tester`: behavior-focused unit/integration/E2E testing.
- `mock-generator`: mocks, fakes, fixtures and builders.
- `debugger`: evidence-first root-cause investigation.
- `api-contract`: API/event/schema compatibility and failure semantics.
- `performance`: latency, concurrency, scaling and cost-performance review.

## Architecture and platform

- `project-scanner`: read-only multi-repository discovery.
- `architecture-designer`: current/target architecture, ADRs and diagrams.
- `platform-architect`: leads cross-domain platform architecture decisions.
- `aws-platform`: AWS managed services, IAM, networking, reliability and cost.
- `terraform-terragrunt`: Terraform/OpenTofu/Terragrunt implementation and review.
- `kubernetes`: Kubernetes/EKS workloads, scheduling, autoscaling and operations.
- `cicd`: CI/CD, GitHub Actions, OIDC, artifacts and release safety.
- `sre`: SLOs, capacity, failure modes, DR and operational risk.
- `observability`: logs, metrics, traces, dashboards and alerting.
- `finops`: AWS/platform cost drivers and cost-performance trade-offs.
- `database`: PostgreSQL/Aurora schema, queries, migrations, HA and backup.
- `networking`: VPC, DNS, CloudFront/WAF, TLS, ingress and private access.

## Language specialists

- `python-specialist`: typed Python services, automation and testing.
- `go-specialist`: Go services, CLIs, concurrency and AWS integrations.

## Security

- `threat-model`: assets, actors, trust boundaries, abuse cases and mitigations.
- `appsec`: application security and business-logic review.
- `iac-security`: Terraform/Kubernetes/AWS security review.
- `supply-chain`: dependencies, CI, images and provenance.
- `secrets`: credential/sensitive-data leakage review with redacted output.
- `pentest`: explicitly authorized, scoped, non-destructive runtime validation.

## Documentation

- `docs-writer`: README, ADR, runbook and migration documentation grounded in verified implementation.

## Independence rules

Implementation agents should not be the only reviewers of their own work. Security findings should be produced by dedicated security agents. Material disagreements go to `arbiter`; high-risk or low-confidence decisions go to `deep-reasoner`; non-trivial completion claims can be audited by `evidence-auditor`.
