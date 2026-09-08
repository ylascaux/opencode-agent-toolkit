# Usage

Start with `just run`. Use `/auto` when routing should be decided automatically.

## Delivery

```text
/ship Add idempotency to this event consumer.
```

The meta-router delegates to `orchestrator`; the orchestrator selects implementation/test/review/security leaves. The implementation agent never self-approves.

## Review

```text
/review Review the current branch before merge.
```

This goes through `review-lead`, which selects only relevant review dimensions.

## Architecture

```text
/architecture Discover the systems under ~/Projects and propose a target AWS platform architecture.
```

This goes directly to `platform-architect`, preserving the two-level delegation depth.

## Security

```text
/security Review the authentication and Terraform changes on this branch.
```

This goes to `security-lead`. Runtime pentesting is used only when an authorized target is explicit.

## Evidence handoff

Delegated agents end with STATUS, SUMMARY, FACTS, ASSUMPTIONS, EVIDENCE, FINDINGS, RESIDUAL RISKS, RECOMMENDED NEXT AGENTS and categorical CONFIDENCE. HIGH means directly verified/reproduced; MEDIUM means strong static/indirect evidence; LOW means unresolved hypothesis or missing proof.

## Model setup

```bash
just configure
just models
```

Prefer independent model families for builder vs reviewer/security when your gateway exposes suitable choices.
