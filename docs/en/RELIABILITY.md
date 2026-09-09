# Agent reliability guardrails

The toolkit combines deterministic runtime safeguards with supervision rules injected into lead agents. The core principle is: **LLMs decide engineering work; deterministic code enforces runtime safety, and ambiguous watchdog signals never destroy work automatically**.

## Reliability profiles

`reliability.json` defines three profiles:

| Profile | Parallel | Queue | Heartbeat | Stall | Child duration | Delegation retries |
|---|---:|---:|---:|---:|---:|---:|
| `cheap` | 2 | 300s | 45s | 120s | 600s | 1 |
| `normal` | 3 | 600s | 60s | 180s | 900s | 2 |
| `premium` | 4 | 900s | 90s | 240s | 1200s | 2 |

`normal` is the default profile. Explicit values in `.env.local` override profile defaults.

Provider-reported monetary budgets are deliberately **not** part of the runtime anymore. `MAX_CHILD_COST` and `MAX_RUN_COST` were removed because provider cost telemetry is not reliable enough to justify destructive session control. Old local values are ignored by the active watchdog wrappers.

## Global and per-lead parallelism

The global limit remains:

```bash
MAX_PARALLEL_SUBAGENTS=3
```

Optional per-lead overrides:

```bash
MAX_PARALLEL_META_ROUTER=2
MAX_PARALLEL_ORCHESTRATOR=3
MAX_PARALLEL_REVIEW_LEAD=3
MAX_PARALLEL_PLATFORM_ARCHITECT=3
MAX_PARALLEL_SECURITY_LEAD=2
```

The runtime tracks active child sessions and launch reservations so bursts cannot race above the configured limit. When all slots are busy, delegation waits in a deterministic queue without another LLM call.

## Approval-first watchdog

OpenCode telemetry can be incomplete while an agent is still reasoning or waiting inside the runtime. Therefore **silence is a suspicion, not proof of a stall**.

The active V1/V2 wrappers disable destructive heuristic watchdog actions for no observable progress, maximum child duration, repeated-result heuristics, and provider-reported cost. The previous watchdog implementations remain isolated as `*-legacy` compatibility code so queueing, delegation retry and task identity behavior can be retained and regression-tested.

### OpenCode V2

V2 loads `./plugins/reliability-approval` alongside the runtime plugin. The approval plugin observes activity independently and emits a `suspected` event when a child appears stalled or exceeds its configured duration.

The TUI asks the user before taking destructive action. `session.interrupt()` is called **only after the user explicitly chooses Kill**.

If the session becomes active again before the decision reaches the server, the decision is considered stale and the session is not interrupted. If the TUI is disconnected, unavailable, or the approval event cannot be delivered, the system fails open and does not kill the session.

Choosing **Keep running** resets the observation window and suppresses repeated prompts for a cooldown period.

### OpenCode V1 / headless usage

V1 does not have a reliable equivalent confirmation surface for this workflow. Heuristic watchdog interruption therefore fails open: the session is preserved rather than automatically killed.

## Retry and task identity

Delegation retry state still preserves the known child `task_id` when a retryable child termination is observed. A retry of the same logical delegation should resume the known child rather than silently create a brand-new leaf.

Completed siblings and the parent lead are not supposed to be restarted merely because one leaf fails.

## Permission waits and child supervision

`WAITING_PERMISSION` is never a stall. A lead with an active child is `WAITING_ON_CHILD`, not stalled simply because the lead itself is quiet.

Generated lead prompts explicitly treat watchdog silence as `STALL_SUSPECTED` only and instruct the lead to wait for an explicit user decision before replacing or cancelling work.

## Checkpoints

The runtime stores metadata checkpoints under:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/opencode-agent-toolkit/runs/<session-id>.json
```

Optional override:

```bash
RELIABILITY_STATE_DIR=$HOME/.local/state/opencode-agent-toolkit/runs
```

Checkpoints contain session/delegation metadata, statuses, timestamps and abort reasons. They do not intentionally copy prompts or project source code.

## Step caps

Step overrides remain ceilings:

```bash
MAX_STEPS_BUILDER=7    # can reduce
MAX_STEPS_BUILDER=999  # cannot exceed the policy/generator boundary
```

`scripts/apply-reliability` effectively applies:

```text
effective steps = min(generated steps, reliability cap)
```

## Expected stop policy

- missing heartbeat/progress -> suspect only, never automatic kill;
- maximum duration -> suspect only, never automatic kill;
- V2 suspected child -> ask user before interrupting;
- V1/headless suspected child -> fail open;
- `WAITING_PERMISSION` -> not stalled;
- active/in-flight tool -> not stalled;
- parallel limit reached -> wait in the runtime queue;
- explicit user-approved kill -> interrupt only that child;
- retryable child termination -> preserve/reuse known `task_id` when possible;
- provider monetary telemetry -> never used as a kill boundary.

## Useful commands

```bash
just reliability
just preflight
just doctor
just check
```

`just reliability` shows the effective timing/parallelism policy and the active approval mode.
