# Agent reliability and cost guardrails

The toolkit applies deterministic safeguards before and during agent execution. The goal is to fail fast on configuration problems, bound expensive loops, and supervise child sessions instead of relying only on prompt discipline.

## Defaults

The default policy lives in `reliability.json`.

- maximum parallel subagents: `3`
- stalled child timeout: `180s`
- maximum child duration: `900s`
- repeated root error limit: `2`
- provider retries: `2`
- watchdog interval: `15s`
- per-agent step caps are lower than the raw generator defaults; the orchestrator and builder are capped at `16` by default

Every value can be overridden from `.env.local` without changing tracked files.

```bash
MAX_PARALLEL_SUBAGENTS=2
SUBAGENT_STALLED_TIMEOUT_SECONDS=240
SUBAGENT_MAX_DURATION_SECONDS=1200
MAX_PROVIDER_RETRIES=1
MAX_STEPS_ORCHESTRATOR=12
MAX_STEPS_BUILDER=14
```

Use `just reliability` to inspect the effective policy.

## Launch sequence

`oc` / `just run` now performs the following sequence:

1. load `.env` and `.env.local`
2. regenerate OpenCode configuration
3. apply reliability step caps and watchdog plugin wiring
4. resolve model tiers
5. run deterministic preflight checks
6. start OpenCode only when preflight passes

Disable the preflight only for troubleshooting with `OPENCODE_PREFLIGHT=0`. `OPENCODE_PREFLIGHT_STRICT=1` turns warnings into failures.

## Preflight

The preflight does not call an LLM. It verifies the selected OpenCode binary, generated config, reliability policy, model tier variables, concurrency configuration, git state, and whether the OpenCode auth command can be executed.

Configuration/auth/provider failures should therefore be discovered before an expensive coding loop starts whenever they can be detected locally.

## Subagent watchdog

The V1 and V2 runtimes use version-specific watchdog plugins.

The watchdog tracks child sessions separately from their root orchestrator. It distinguishes activity from useful progress and does not classify a child waiting for a permission decision as stalled.

A child may be interrupted when it exceeds its maximum duration or has no material progress beyond the configured stalled timeout. V1 also stops repeated identical runtime/tool errors. V2 additionally overrides provider retry decisions so HTTP `400`, `401`, `403`, and `404` failures are terminal, while `429` and server failures are retryable only within the configured retry budget.

## Maximum parallelism

`MAX_PARALLEL_SUBAGENTS` controls the maximum number of active children per parent session. The default is `3`.

The orchestrator prompt is also generated with the same value, so both the model and runtime guard agree on the concurrency budget. When the runtime guard sees the limit already reached, another delegation is rejected and the orchestrator must wait for an existing child to complete.

Recommended values:

- `1`: expensive/premium model runs, debugging fragile environments
- `2`: conservative default for paid API usage
- `3`: toolkit default; good balance for normal development
- `4+`: only when rate limits and cost are understood

## Stop policy

Lead agents are explicitly instructed to stop retry chains when the same root cause repeats, to reuse completed handoffs, and to treat `WAITING_PERMISSION` differently from `STALLED`.

The intended behavior is:

- auth/config/permission/provider error -> fail fast
- temporary `429`/`5xx` -> bounded retry
- repeatable code/test failure with new evidence -> continue within the step budget
- same root cause without new evidence -> stop or route once to a distinct specialist
- stalled child -> interrupt, preserve evidence, then reroute or report the blocker

## Remaining cost control

Step caps, retry caps, duration limits and parallelism substantially bound cost, but a hard euro budget requires reliable per-request cost telemetry from the selected provider/gateway. The toolkit should only enforce a monetary hard stop when that telemetry is authoritative; otherwise token/call/step/time budgets are safer than pretending an estimated cost is exact.
