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
```

The lead selects only relevant domains.

## Evidence-driven architecture

Architecture recommendations separate observed facts, heuristic signals, assumptions and proposed target-state decisions. Inventory v2 includes components, interfaces, AWS resources, data stores, signals, file/line evidence, confidence and evidence-backed relationships.

A diagram edge should be supported by evidence or labeled as proposed/assumed.

## Required architecture output

For non-trivial platform design include context/constraints, current and target state, component/data/control flows, trust boundaries, SLO/availability model, scaling/capacity, failure domains, security controls, operational ownership, upgrades/migrations/rollback, DR/RTO/RPO where relevant, cost drivers, decision matrix/rejected alternatives and residual risks.
