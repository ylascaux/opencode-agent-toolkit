# Structured research pipeline

This toolkit provides reusable OpenCode agents and machine-readable envelopes for evidence-driven external research. It deliberately does **not** own product-specific schemas, persistence, scoring, canonical datasets, or workflow-engine configuration.

## Boundary

The consuming application owns:

- scheduling and workflow orchestration (for example n8n);
- job persistence, claiming, idempotency and result storage;
- domain schemas and deterministic schema validation;
- canonical entity/deduplication rules;
- business scoring, approval rules and publishing.

The toolkit owns:

- `source-discovery`: find a compact candidate source set;
- `structured-extractor`: extract schema-shaped candidate data from supplied evidence;
- `entity-resolver`: assess identity conflicts without mutating canonical records;
- `evidence-auditor`: independently check MEDIUM-confidence or partially verified outputs;
- `deep-reasoner`: resolve HIGH-risk, materially conflicting, or persistently LOW-confidence cases;
- runtime retry, parallelism, step and cost guardrails already enforced by the toolkit.

A workflow engine such as n8n belongs in the consuming application repository. No n8n workflow, credential, database, queue, or product-specific rule should be added to this toolkit.

## Recommended flow

```text
external workflow / scheduler
        |
        v
Research Job envelope
        |
        v
OpenCode orchestrator
        |
        +--> source-discovery       (LOW is acceptable for bounded discovery)
        |
        +--> structured-extractor   (MEDIUM)
        |
        v
caller-owned deterministic schema validation
        |
        +--> validation error -> one focused retry with exact errors
        |
        +--> identity ambiguity -> entity-resolver (MEDIUM)
        |
        +--> MEDIUM confidence / partial evidence -> evidence-auditor
        |
        +--> HIGH risk, material conflict, or persistent LOW confidence
        |       -> deep-reasoner (HIGH)
        |
        v
Research Result envelope
        |
        v
caller-owned deterministic checks / persistence / publishing
```

The LOW -> MEDIUM -> HIGH path is an escalation ladder, not a mandatory chain. Start with the cheapest sufficient agent and escalate only when evidence, validation errors, risk, or uncertainty justify it.

## Contracts

`contracts/research-job.schema.json` is the input envelope. `target_schema` is optional and caller-owned: the toolkit may consume it but does not become its source of truth.

`contracts/research-result.schema.json` is the output envelope. Its `data` field is intentionally generic. A syntactically valid Research Result does **not** prove that `data` satisfies the consuming application's domain schema.

The caller must validate both:

1. the generic result envelope;
2. the domain payload against its own schema and deterministic rules.

## Confidence and escalation

- **HIGH confidence**: direct and sufficient evidence supports the material claims. Continue to caller-owned deterministic checks.
- **MEDIUM confidence**: evidence is strong but indirect, incomplete, or requires an independent check. Run `evidence-auditor` before automated acceptance.
- **LOW confidence**: unresolved ambiguity, missing evidence, or material conflict remains. Do not auto-accept. Retry only when a concrete validation/evidence gap can be corrected; otherwise escalate or return blocked.

Risk and confidence are separate. A HIGH-risk decision may require `deep-reasoner` even when the evidence appears strong.

## Retry discipline

Never repeat the same prompt blindly. A retry must carry new information such as exact schema validation errors, a failed source locator, a missing field list, or a specific evidence conflict. Respect the caller's `max_attempts`, the toolkit runtime budgets, and the configured parallelism cap.

Transient provider/tool failures are handled by the toolkit reliability layer. Domain validation failures are caller-owned and should be fed back as structured correction input rather than hidden.

## External automation

For known structured jobs, an external worker may invoke the toolkit's `orchestrator` non-interactively and request a `Research Result` JSON response. The external workflow should treat OpenCode as an execution dependency, not as the database or source of business truth.

Keep the execution boundary replaceable: n8n can be replaced later without changing the research agents, and model/provider profiles can change without changing the consuming product's domain model.
