# Agent reliability and cost guardrails

The toolkit combines deterministic runtime safeguards with supervision rules injected into lead agents. The core principle is: **LLMs decide engineering work; deterministic code decides runtime safety boundaries**.

## Reliability profiles

`reliability.json` defines three profiles:

| Profile | Parallel | Queue | Stall | Child duration | Retries | Child cost* | Run cost* |
|---|---:|---:|---:|---:|---:|---:|---:|
| `cheap` | 2 | 300s | 120s | 600s | 1 | 0.25 | 1.00 |
| `normal` | 3 | 600s | 180s | 900s | 2 | 0.50 | 2.00 |
| `premium` | 4 | 900s | 240s | 1200s | 2 | 1.50 | 5.00 |

`normal` is the default profile. Cost values marked `*` use **the value reported by OpenCode/provider in its native unit**. The toolkit does not invent an EUR conversion.

```bash
RELIABILITY_PROFILE=normal
```

Any explicit value in `.env.local` overrides the selected profile.

## Global and per-lead parallelism

The global limit remains:

```bash
MAX_PARALLEL_SUBAGENTS=3
```

Per-lead overrides are also supported:

```bash
MAX_PARALLEL_META_ROUTER=2
MAX_PARALLEL_ORCHESTRATOR=3
MAX_PARALLEL_REVIEW_LEAD=3
MAX_PARALLEL_PLATFORM_ARCHITECT=3
MAX_PARALLEL_SECURITY_LEAD=2
```

If a lead-specific value is unset, the global limit is used.

The runtime tracks actual child sessions and launch reservations. A reservation is consumed as soon as the child appears through events or `session.children()`. This prevents both:

- bursts racing above the configured limit;
- temporarily double-counting the same launch as both pending and active.

When all slots are busy, delegation waits in a deterministic queue **without another LLM call**. `SUBAGENT_QUEUE_TIMEOUT_SECONDS` bounds that wait.

## Preflight before the first expensive model call

`oc` / `just run` executes deterministic checks before starting OpenCode:

- selected binary exists;
- generated config is valid JSON;
- matching V1/V2 watchdog is present and wired;
- reliability profile is valid;
- runtime numeric values are valid;
- all models actually configured on agents are exposed by `opencode models`;
- auth is available for known providers that use OpenCode authentication;
- Git workspace state is observable.

Controls:

```bash
OPENCODE_PREFLIGHT=1
OPENCODE_PREFLIGHT_AUTH=1
OPENCODE_PREFLIGHT_MODELS=1
# OPENCODE_PREFLIGHT_STRICT=1
```

The script remains compatible with the Bash 3 shipped by default on macOS.

## V1 and V2 watchdog parity

V1 and V2 keep the same functional safeguards:

- individual child-session tracking;
- `lastActivityAt` versus `lastProgressAt`;
- `WAITING_PERMISSION` excluded from stall detection;
- maximum duration;
- activity-aware no-progress timeout;
- repeated-failure detection;
- bounded queue and parallelism;
- `session.children()` reconciliation when available;
- metadata checkpoints;
- provider-reported cost budgets when telemetry exists.

V2 additionally keeps the provider retry hook:

```text
400 / 401 / 403 / 404 -> terminal
429                  -> bounded retry
5xx                  -> bounded retry
```

## Activity-aware stall detection

A child is no longer considered stalled merely because it has not emitted a file edit, diff, todo update, or other material-progress event recently. The watchdog now requires all of the following before interrupting it:

1. no material progress for longer than `SUBAGENT_STALLED_TIMEOUT_SECONDS`;
2. no runtime/message heartbeat for longer than `SUBAGENT_HEARTBEAT_TIMEOUT_SECONDS`;
3. no tool call still in flight;
4. the same stale condition is observed again on the next watchdog cycle.

Example defaults for the `normal` profile:

```bash
SUBAGENT_HEARTBEAT_TIMEOUT_SECONDS=60
SUBAGENT_STALLED_TIMEOUT_SECONDS=180
SUBAGENT_WATCH_INTERVAL_SECONDS=15
```

This protects long reasoning, reading, analysis, and streamed message generation from false-positive cancellation while retaining deterministic stall recovery.

When the watchdog does interrupt a retryable child, it persists the existing delegation and its `task_id` as `retryable_failed` **before** sending the interrupt. A retry of the same logical delegation therefore resumes the known task instead of silently creating a fresh child and losing already-produced context.

## Repeated tool-loop detection

The watchdog stores a signature for a tool call and its result. If a child repeatedly executes **the same tool with the same arguments and receives the same result**, that activity stops counting as progress.

Once `MAX_SAME_ERROR` is reached, the child may be interrupted.

This covers loops such as:

```text
command A -> result X
command A -> result X
command A -> result X
```

that a simple step counter cannot diagnose well.

## Provider-reported cost budgets

```bash
MAX_CHILD_COST=0.50
MAX_RUN_COST=2.00
```

`0` disables the corresponding monetary boundary.

The guard is enforced only when OpenCode/provider reports usable cost telemetry. If no cost is reported, **no estimate is fabricated**: steps, duration, stall detection, retries, depth, and parallelism remain the safe deterministic boundaries.

`MAX_CHILD_COST` interrupts a child above its reported budget. `MAX_RUN_COST` interrupts the run session family when the reported total exceeds the configured limit.

## Checkpoints

The watchdog persists **metadata only**, never prompts or copies of source code:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/opencode-agent-toolkit/runs/<session-id>.json
```

Optional override:

```bash
RELIABILITY_STATE_DIR=$HOME/.local/state/opencode-agent-toolkit/runs
```

A checkpoint records, among other fields:

- session ID and parent;
- agent;
- status;
- abort reason;
- delegation retry state when applicable;
- provider-reported cost;
- start/activity/progress timestamps.

The OpenCode session and structured handoffs remain the source of truth for detailed work content.

## Step caps

Step overrides are **ceilings**, not absolute values that can increase an agent's freedom.

```bash
MAX_STEPS_BUILDER=7    # can reduce
MAX_STEPS_BUILDER=999  # cannot exceed the generator boundary
```

`scripts/apply-reliability` effectively applies:

```text
effective steps = min(generated steps, reliability cap)
```

## Stop policy

Expected behavior:

- non-retryable auth/config/provider/model error -> stop quickly;
- `429` / `5xx` -> bounded retry;
- same root failure without new evidence -> stop;
- same tool + same args + same result -> detectable loop;
- no progress **and** no heartbeat, confirmed on a second watchdog cycle -> interrupt;
- active or in-flight work -> not a stall;
- child over duration -> interrupt;
- child over reported cost -> interrupt when telemetry exists;
- `WAITING_PERMISSION` -> not a stall;
- parallel limit reached -> wait in the runtime queue;
- retryable watchdog abort -> preserve and reuse the known `task_id`;
- blocked/aborted child -> consume its handoff/checkpoint before deciding on a replacement.

## Useful commands

```bash
just reliability
just preflight
just doctor
just check
```

`just reliability` shows the effective policy after profile selection and local overrides.
