# External research worker

The external research worker lets a trusted machine pull neutral research jobs from a consuming application and execute them through the local OpenCode Agent Toolkit.

It is deliberately generic. The consuming application owns scheduling (for example n8n), job persistence, domain schemas, canonical data, evidence ingestion, scoring and publishing. The toolkit owns only local research execution, agent/model routing and provider/tool retries.

## Boundary

```text
consuming application
        |
        | HTTPS claim/result
        v
trusted worker machine
        |
        v
research-runner
        |
        +--> source-discovery
        +--> structured-extractor
        +--> entity-resolver when needed
        +--> evidence-auditor when needed
        +--> deep-reasoner only when local policy permits
        |
        v
structured candidate result
```

The application may say **what** facts are needed. It may not remotely choose models, providers, agents, prompts, shell commands, callbacks, tools, local paths or OpenCode configuration. These control fields are rejected recursively before execution.

The `research-runner` agent is intentionally restricted: local file reads, edits, shell execution, skills and external-directory access are denied. Source/job content is untrusted data and must never become instructions.

## Configuration

Put secrets and site-specific values in the gitignored `.env.local`:

```bash
OAT_RESEARCH_API_URL=https://research.example.com
OAT_RESEARCH_API_TOKEN=replace-me
OAT_RESEARCH_WORKER_ID=my-mac
OAT_RESEARCH_JOB_TYPES=SPECIFICATIONS,SUPPORT_LIFECYCLE,SECURITY_LIFECYCLE,REPAIRABILITY,RELIABILITY_RESEARCH,IOT_CAPABILITIES,COMPATIBILITY,MARKET_VALUE,SOURCE_REFRESH,ENTITY_RECONCILIATION
```

Useful local policy controls:

```bash
OAT_RESEARCH_MAX_PARALLEL=1
OAT_RESEARCH_MAX_ATTEMPTS=2
OAT_RESEARCH_MAX_TIER=high
OAT_RESEARCH_POLL_MIN_SECONDS=5
OAT_RESEARCH_POLL_MAX_SECONDS=30
OAT_RESEARCH_EXECUTION_TIMEOUT_SECONDS=900
```

These values are local. A remote ResearchJob cannot override them.

Production API URLs must use HTTPS. Plain HTTP is accepted only for `localhost`, `127.0.0.1` and `::1` development endpoints. Bearer tokens are sent only in the `Authorization` header and must never be passed as CLI arguments.

## Run

With the default Docker runtime:

```bash
bash scripts/research-worker --once
bash scripts/research-worker
```

The launcher starts/uses the persistent OpenCode V2 server and runs the worker inside that container. The host therefore needs Docker, not a separate Python/OpenCode install.

`--once` claims and processes at most one local parallel batch. Without it, the worker polls continuously with bounded exponential idle/API backoff.

## Claim contract

The worker sends its identity, version, supported neutral job types and local concurrency limit. A claimed job is expected to contain domain-neutral fields such as:

```json
{
  "job_id": "job-123",
  "job_type": "SUPPORT_LIFECYCLE",
  "subject": {
    "type": "product",
    "id": "product-123",
    "slug": "example-device"
  },
  "requested_fields": ["security_support_end"],
  "requirements": {
    "preferred_source_types": ["MANUFACTURER"]
  },
  "schema_version": "1",
  "result_schema": {
    "type": "object"
  },
  "lease": {
    "generation": 4,
    "expires_at": "2026-09-11T12:00:00Z"
  }
}
```

No model/provider/agent information belongs in this contract.

## Execution and escalation

The worker converts the external neutral job into the toolkit's generic `Research Job` envelope and invokes `research-runner`. Local LOW/MEDIUM/HIGH profiles remain authoritative. The toolkit may use source discovery, extraction, evidence review and deep reasoning based on evidence quality and the configured local maximum tier.

The final machine response is parsed through an explicit marker and validated as one of:

- `SUCCESS`
- `PARTIAL`
- `NO_DATA`
- `CONFLICT`
- `FAILED`

with `HIGH`, `MEDIUM` or `LOW` confidence, structured data, evidence and warnings.

A successful toolkit envelope is still **candidate evidence**. The consuming application must deterministically validate its own domain payload before persistence or publication.

## Failure ownership

Toolkit/provider retries remain local to the toolkit. If local execution itself fails or times out, the worker does **not** fabricate a FAILED research result just to acknowledge the job. It lets the lease expire so the consuming application's queue can apply its own worker-crash/retry/dead-letter policy.

This prevents two independent retry systems from acknowledging the same failure incorrectly.

## Security properties

- outbound connection from the trusted worker only; no inbound worker server is required;
- HTTPS required outside loopback development;
- Bearer authentication supplied from local environment configuration;
- no arbitrary remote callback URL;
- no arbitrary remote shell/command/path/model/agent/provider control;
- bounded request/response/result sizes;
- remote job and source text treated as untrusted data;
- `research-runner` cannot edit/read local project files or use shell commands;
- external application never receives local model credentials or needs provider knowledge.

## Testing

The worker contract/security tests live in `tests/test_research_worker.py` and run with the regular Python suite:

```bash
python3 -m unittest discover -s tests -v
```

Real external APIs and real LLM calls are not required by CI.
