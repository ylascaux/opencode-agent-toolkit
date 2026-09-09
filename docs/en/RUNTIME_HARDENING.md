# Watchdog runtime hardening

This document summarizes the runtime invariants added to prevent ghost queue reservations, false-positive loop detection, cost enforcement against the wrong session, and delegated agents becoming stuck in interactive terminal programs.

## Fallback call IDs

When OpenCode provides a native `callID`, the runtime uses it directly.

When no native ID is available, the toolkit creates a unique ID and keeps a FIFO queue per `session + tool + arguments` signature. Two identical calls started concurrently therefore receive distinct IDs, and `execute.after` events consume those IDs in launch order.

This prevents ghost reservations from artificially exhausting subagent queue capacity.

## Progress-aware loop detection

The `same tool + same arguments + same result` detector is scoped to a progress window.

Material progress (`session.diff`, file edits, todo updates, permission replies, or a distinct successful tool outcome) advances the progress epoch. An identical call observed after that boundary is not treated as a continuation of an older loop.

## Session resolution for message events

Message events contain both a message ID and a session ID. The watchdog always prioritizes `sessionID` when updating activity, provider-reported cost, and runtime limits.

This ensures `MAX_CHILD_COST` and `MAX_RUN_COST` are enforced against the actual agent session rather than an ephemeral message object.

## Non-interactive shell invariant

Agent shell execution is non-interactive by construction, not only by prompt convention.

The shared `.opencode/plugins/non-interactive-shell.js` policy injects:

- `PAGER=cat`;
- `GIT_PAGER=cat`;
- `GH_PAGER=cat`;
- `SYSTEMD_PAGER=cat`;
- `BAT_PAGER=cat`;
- `AWS_PAGER=`;
- `GIT_TERMINAL_PROMPT=0`;
- `GH_PROMPT_DISABLED=1`;
- `TF_INPUT=0`;
- `TF_IN_AUTOMATION=1`;
- `CI=1`.

OpenCode V1 applies this policy through the `shell.env` plugin hook. OpenCode V2 applies it through the shell `create.before` hook before every agent shell is created. V2 intentionally fails closed if that shell hook is unavailable, because silently dropping the non-interactive invariant could leave delegated agents waiting for keyboard input.

This runtime layer complements the default permission policy, which denies common pagers/TUIs/editors and interactive Git modes, and the common prompt, which tells agents to stop as `BLOCKED` when no safe non-interactive path is known.

## Behavioral tests

`just runtime-test` runs Node tests that verify:

- unique FIFO fallback IDs for concurrent identical calls;
- loop-detector reset after material progress;
- provider retry policy (`401/404` terminal, bounded `429/5xx` retries);
- subagent reservation release after `execute.after`;
- child-cost enforcement against the real child session;
- `WAITING_PERMISSION` exemption from stall detection and resumption after the permission is answered;
- shared non-interactive shell environment injection, including V1 `shell.env` behavior.

Python tests additionally verify that every generated agent prompt contains the non-interactive contract and that its `ALLOW`/`ASK`/`DENY` capability map matches the generated effective V1 permission tree.

`just check` includes these tests in addition to generated-config validation.
