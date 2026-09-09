# Watchdog runtime hardening

This document summarizes the runtime invariants added to prevent ghost queue reservations, false-positive loop detection, and cost enforcement against the wrong session.

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

## Behavioral tests

`just runtime-test` runs Node tests that verify:

- unique FIFO fallback IDs for concurrent identical calls;
- loop-detector reset after material progress;
- provider retry policy (`401/404` terminal, bounded `429/5xx` retries);
- subagent reservation release after `execute.after`;
- child-cost enforcement against the real child session;
- `WAITING_PERMISSION` exemption from stall detection and resumption after the permission is answered.

`just check` now includes these tests in addition to Python tests and generated-config validation.
