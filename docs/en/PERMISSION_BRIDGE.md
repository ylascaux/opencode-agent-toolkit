# OpenCode V1 subagent permission bridge

OpenCode V1 permission requests belong to the session that emitted them. A delegated child or grandchild can therefore reach an `ask` permission while the user is still looking at the parent session.

OpenCode currently exposes TUI APIs to show a toast and open the session selector, but it does not expose a plugin API that selects a session directly by ID. The toolkit bridges that UX gap without changing the permission decision.

## Behavior

When `permission.asked` is emitted by the root session, the toolkit does nothing and lets the native OpenCode TUI handle it.

When `permission.asked` is emitted by a delegated session, the V1 reliability wrapper:

1. resolves the child/parent relationship from observed session events, with `session.get` as a fallback;
2. shows a warning toast identifying the agent, child session and requested permission;
3. opens the native OpenCode session selector so the user can select that child and answer the original permission prompt;
4. keeps the permission itself untouched: the toolkit never converts `ask` to `allow` or `deny`;
5. deduplicates replay of the same permission request so the TUI is not spammed.

The reliability watchdog continues to treat `WAITING_PERMISSION` as an intentional wait rather than a stall. The bridge makes that wait visible instead of silently auto-resolving it.

## Configuration

The default behavior is intentionally user-visible:

```bash
PERMISSION_BRIDGE_TOAST=1
PERMISSION_BRIDGE_OPEN_SESSIONS=1
```

Set `PERMISSION_BRIDGE_OPEN_SESSIONS=0` if you want the warning toast but do not want the toolkit to open the session selector automatically.

Set `PERMISSION_BRIDGE_TOAST=0` to disable the toast. This is not recommended unless another UI surface reliably exposes delegated permission requests.

## Current OpenCode limitation

As of September 2026, plugins cannot directly switch the TUI to an arbitrary child session by ID. The bridge therefore opens the native session selector and tells the user which child is waiting. If OpenCode adds a supported `select-session` API later, the bridge can be upgraded to focus the blocked child directly.
