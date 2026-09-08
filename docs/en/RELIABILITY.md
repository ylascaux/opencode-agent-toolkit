# Runtime Reliability

The toolkit uses two complementary layers: deterministic runtime enforcement and agent-level supervision rules. The goal is to fail early, bound cost, and preserve completed work instead of discovering an authentication, provider, or stalled-subagent problem after a long run.

## Preflight

The launcher runs `scripts/preflight` before OpenCode starts the first model session. It checks the selected binary, resolved models, runtime settings, the watchdog installation, authentication for known authenticated providers, provider model availability, and basic Git workspace state.

A blocking failure exits before any model call:

```text
Preflight failed with 1 blocking issue(s). No agent session was started.
```

Disable individual checks only when you intentionally accept the risk:

```bash
OC_PREFLIGHT=0
OC_PREFLIGHT_AUTH=0
OC_PREFLIGHT_MODELS=0
```

## Conservative step limits

`generate-config` still owns the agent catalog and permissions. `apply-runtime-policy` applies a second deterministic pass with conservative step ceilings and injects delegated-work supervision into the five lead agents.

Defaults keep every agent at 16 steps or fewer. Override globally or per agent in `.env.local`:

```bash
OC_DEFAULT_AGENT_STEPS=12
OC_STEPS_ORCHESTRATOR=16
OC_STEPS_BUILDER=14
```

## Subagent watchdog

OpenCode V1 loads `plugins/runtime-guardrails.js` through the managed global symlink installed by:

```bash
just install-user
```

The plugin is intentionally inert for ordinary OpenCode sessions. The toolkit launcher activates it with `OPENCODE_TOOLKIT_RUNTIME_GUARDS=1`.

The watchdog tracks child sessions separately from the root session and distinguishes activity from progress. It reacts to session, permission, message, file, todo, and tool lifecycle signals without asking an LLM for status updates.

It can abort a child when any deterministic boundary is crossed:

- non-retryable authentication/provider/configuration failure;
- the same failure repeats beyond the configured limit;
- the same tool call keeps producing the same result;
- no progress for the stall timeout;
- maximum child duration exceeded;
- child cost budget exceeded when OpenCode reports cost;
- whole-run cost budget exceeded when OpenCode reports cost.

`WAITING_PERMISSION` is explicitly excluded from stall detection.

## Configurable parallelism

`OC_MAX_PARALLEL_SUBAGENTS` is a hard launch gate. Extra child launches wait in a queue before the subagent tool executes, so queued work does not consume another model call merely to wait.

```bash
OC_MAX_PARALLEL_SUBAGENTS=3
```

Lead-specific overrides are also supported:

```bash
OC_MAX_PARALLEL_META_ROUTER=2
OC_MAX_PARALLEL_ORCHESTRATOR=3
OC_MAX_PARALLEL_REVIEW_LEAD=3
OC_MAX_PARALLEL_PLATFORM_ARCHITECT=3
OC_MAX_PARALLEL_SECURITY_LEAD=2
```

The lead agent is resolved from OpenCode's chat hooks. If it cannot be resolved, the global limit is used.

## Profiles

Three watchdog profiles provide initial defaults:

| Profile | Parallel | Stall | Child duration | Child cost | Run cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| `cheap` | 2 | 120 s | 420 s | 0.25 | 1.00 |
| `normal` | 3 | 180 s | 600 s | 0.50 | 2.00 |
| `premium` | 4 | 240 s | 900 s | 1.50 | 5.00 |

Cost values use the cost unit reported by OpenCode/provider, normally USD. Cost limits are an additional barrier, not the only one: providers that do not report cost are still bounded by steps, duration, concurrency, repeated-failure detection, and stall detection.

Set the profile with:

```bash
OC_RUNTIME_PROFILE=normal
```

Explicit `OC_*` values override profile defaults.

## Checkpoints

The watchdog writes metadata checkpoints under:

```text
${XDG_STATE_HOME:-~/.local/state}/opencode-agent-toolkit/runs/<session-id>.json
```

A checkpoint records the child session ID, parent, agent, status, abort reason, provider-reported cost, and activity/progress timestamps. It intentionally does not copy prompt or source-code contents into the state directory. The OpenCode session remains the source of truth for resuming detailed work.

## Lead supervision

The five lead agents receive additional instructions to:

- obey the runtime concurrency queue instead of bypassing it;
- treat repeated activity without new evidence as non-progress;
- consume an aborted/blocked child's existing evidence before replacing it;
- resume from the last completed gate rather than restarting the full workflow;
- never duplicate a child that is still active;
- treat permission waiting separately from stalls.

The important separation is: **LLMs decide engineering work; deterministic code decides runtime safety boundaries.**

## Commands

```bash
just install-user   # installs/refreshes the launcher and watchdog symlink
just preflight      # runs checks without starting a model session
just doctor         # reports runtime limits and watchdog installation
just check          # regenerates bounded configs and runs tests
```

## OpenCode V2 note

The current full watchdog implementation targets the stable V1 plugin API used by the toolkit default. V2 still receives bounded steps and lead supervision, but the V1 runtime plugin is not loaded into V2. `preflight` prints that degraded-mode warning explicitly rather than pretending the watchdog is active.
