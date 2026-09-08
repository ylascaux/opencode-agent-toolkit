# Architecture

The toolkit is organized as multiple planes with deliberately separated responsibilities.

## 1. Control plane

`meta-router` is the default entry point. It classifies the request and chooses the minimum sufficient route. It should not implement directly.

`orchestrator` owns multi-step execution. It coordinates implementation, testing, review and the relevant security/operational gates.

`arbiter` resolves material disagreements. `deep-reasoner` handles high-risk, ambiguous or low-confidence decisions. `evidence-auditor` checks whether completion claims are actually supported by reproducible evidence.

## 2. Engineering plane

General engineering agents:

```text
brainstorm -> planner -> builder/specialist -> tester -> reviewer
```

Specialized implementation/review agents include Python, Go, Terraform/Terragrunt, CI/CD, API contracts, performance, database and networking.

## 3. Platform architecture council

For architecture work, the router can compose:

```text
project-scanner
      |
      v
platform-architect
  |-- architecture-designer
  |-- aws-platform
  |-- kubernetes
  |-- terraform-terragrunt
  |-- networking
  |-- database
  |-- sre
  |-- observability
  |-- finops
  |-- threat-model
  `-- iac-security
```

The council must separate observed facts from assumptions and recommendations. Important decisions should include failure modes, migration/rollback, security impact, operational burden and cost drivers.

## 4. Security plane

Security is intentionally independent from the builder:

```text
threat-model
appsec
iac-security
supply-chain
secrets
pentest
```

The router selects only the gates relevant to the changed attack surface.

## 5. Evidence plane

The system treats evidence as a first-class artifact. Depending on the task, evidence can include:

- diffs and changed files;
- exact test commands/results;
- Terraform/OpenTofu validation and plans;
- logs, metrics and traces;
- safe HTTP/runtime validation;
- source inventory JSON;
- explicit assumptions and unresolved questions.

`evidence-auditor` classifies important claims as verified, partially verified, unverified or contradicted.

## 6. Multi-repository discovery

`project-scanner` can read `PROJECTS_ROOT` (default `$HOME/Projects`) without modifying projects. The Python scanner normalizes repository metadata into `architecture-inventory.json`, allowing architecture agents to reason from a compact, machine-readable source instead of repeatedly crawling every repository.

## 7. Model independence

Every agent has its own model variable. This enables a cheap scanner, a strong coding model, a separate reviewer family, and a deep reasoning model only when escalation is justified.
