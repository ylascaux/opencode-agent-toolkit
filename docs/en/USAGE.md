# Usage

The main entry points are high-level commands routed through `meta-router`.

## `/auto`

General adaptive routing:

```text
/auto Review this service and tell me what should be improved before production.
```

Use when you do not want to choose the workflow yourself.

## `/ship`

Implementation workflow:

```text
/ship Add idempotency to this webhook handler and include tests.
```

Typical route: classify -> plan if needed -> narrow implementation specialist -> tests -> independent review -> relevant security gates -> evidence audit.

## `/review`

Independent review of a branch/change/component:

```text
/review Review the current diff for correctness, compatibility, security and performance regressions.
```

Specialists such as API-contract, database, networking or performance are added only when relevant.

## `/architecture`

Architecture council:

```text
/architecture Analyze the services under ~/Projects and propose a target AWS architecture with migration and rollback.
```

The workflow can combine project discovery, platform architect, AWS, Kubernetes, Terraform, database, networking, SRE, observability, FinOps and security specialists.

## `/security`

Adaptive defense-in-depth review:

```text
/security Review this Terraform + API change and validate exploitable issues against localhost when appropriate.
```

Pentest validation remains explicitly scoped and non-destructive.

## `/debug`

Evidence-first debugging:

```text
/debug Find the root cause of this timeout and add a regression test.
```

The debugger ranks/falsifies hypotheses before applying a minimal fix.

## `/incident`

Incident workflow:

```text
/incident Investigate elevated 5xx on the API since the last deployment.
```

Routes to debugger, SRE, observability and affected domain specialists. Separate facts from hypotheses, define blast radius, mitigation/rollback and follow-up verification.

## `/cost`

FinOps and performance workflow:

```text
/cost Analyze this EKS platform and identify the largest savings opportunities without weakening reliability.
```

## Direct agent calls

You can still call a specialist directly when you know what you need:

```text
@terraform-terragrunt Review this module.
@appsec Review this authentication flow.
@project-scanner Inventory ~/Projects.
```

Use direct calls for narrow work; use high-level commands when coordination, independence or escalation matters.
