# Architecture

## Architecture council

```text
meta-router
  -> platform-architect
       -> project-scanner
       -> architecture-designer
       -> aws-platform
       -> terraform-terragrunt
       -> kubernetes
       -> cicd
       -> networking
       -> database
       -> sre
       -> observability
       -> finops
       -> threat-model
       -> iac-security
       -> docs-writer
```

The lead selects only relevant domains. When durable documentation is requested, `platform-architect` stabilizes the design and delegates the actual file writing to `docs-writer`; the architecture lead stays non-editing.

## Delegation economy

Lead agents start from the evidence they can inspect directly and use the smallest sufficient set of child agents. A technology being present in the repository is not enough to justify a specialist task by itself.

For example, finding `.tf`, `.hcl` or Terragrunt files does not automatically trigger `terraform-terragrunt`. That specialist is useful when module boundaries, state, provider behavior, lifecycle/replacement, Terragrunt dependency semantics or migration risk materially affect the architecture or need specialist verification.

The same rule applies to AWS, Kubernetes, networking, database, SRE, observability and FinOps domains. Related discovery questions should be grouped instead of sending several children over the same evidence. Once a child returns a complete handoff, the parent should consume it and continue rather than dispatching the same task again unless the evidence is incomplete, stale or contradictory.

Independent verification remains an intentional exception: a reviewer may re-read the same primary evidence because independence requires not trusting the producer handoff as proof.

## Independent architecture review

Architecture delivery is intentionally staged:

```text
platform-architect
      |
      v
completed architecture artifact
      |
      +--------------------+
      |                    |
      v                    v
 review-lead          security-lead
 independent review   adaptive security gate
      |                    |
      +---------+----------+
                |
                v
          final synthesis
```

`review-lead` must re-check the artifact against direct repository evidence rather than accepting the producer handoff as proof. It can use `project-scanner` plus only the relevant platform dimensions such as AWS, Kubernetes, SRE, observability, FinOps, database, networking and IaC security.

When the completed artifact changes trust boundaries, IAM, public exposure, secrets or infrastructure-security posture, `security-lead` is an additional gate. The independent review and security gate should run in parallel when they are read-only consumers of the same completed artifact and neither depends on the other.

The producing `platform-architect` path never acts as the final independent reviewer of its own artifact.

## Evidence-driven architecture

Architecture recommendations separate observed facts, heuristic signals, assumptions and proposed target-state decisions. Inventory v2 includes components, interfaces, AWS resources, data stores, signals, file/line evidence, confidence and evidence-backed relationships.

A diagram edge should be supported by evidence or labeled as proposed/assumed.

The review-ready handoff should include the artifact path, major decisions, rejected alternatives, assumptions, evidence map, migration/rollback, residual risks and operational ownership concerns.

## Required architecture output

For non-trivial platform design include context/constraints, current and target state, component/data/control flows, trust boundaries, SLO/availability model, scaling/capacity, failure domains, security controls, operational ownership, upgrades/migrations/rollback, DR/RTO/RPO where relevant, cost drivers, decision matrix/rejected alternatives and residual risks.

Use `/architecture-review` when an existing architecture artifact needs an independent review without running a new design pass first.
