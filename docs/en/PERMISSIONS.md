# Agent permissions

Agent permissions have one source of truth and are resolved during configuration generation.

- `agents/_defaults/permissions.json` defines the common baseline inherited by every agent.
- `agents/<name>/permissions.json` deep-merges agent-specific overrides into that baseline.
- `agents/<name>/agent.json` defines the delegation graph through `parents`; task/subagent permissions are generated from that graph and cannot be manually overridden in `permissions.json`.
- Run `just config` after changing an agent or permission policy.

## Single source of truth

The same effective permission tree drives both outputs:

1. the OpenCode V1/V2 runtime ACL;
2. the generated `## Effective capabilities` section embedded in each agent prompt.

Agents therefore see the capabilities that the generator actually grants them. Do not maintain a separate hand-written tool list in prompts.

The generated section separates permissions into:

- `ALLOW`: usable without an approval prompt;
- `ASK`: requires runtime/user approval;
- `DENY`: must not be attempted.

Resource-specific rules refine wildcard rules. Delegation is also rendered explicitly, so an agent sees only the child agents its generated `task`/`subagent` permission allows.

## Non-interactive baseline

All agents are required to execute tools and shells non-interactively. This is enforced in layers:

- the common prompt forbids interactive pagers, TUIs, editors, REPLs, menus and confirmation prompts;
- the default shell policy explicitly denies common interactive programs such as `less`, `more`, `man`, terminal editors, `top`/`htop`, `watch`, `fzf`, `lazygit` and `tig`;
- interactive Git modes such as `git add -p` and `git rebase -i` are denied;
- read-only Git commands have explicit `git --no-pager ...` allow rules;
- the runtime injects non-interactive pager/prompt environment variables into every agent shell as defense in depth.

If an operation is only available through an interactive interface and the agent does not know a safe non-interactive equivalent, it must stop and report the work as blocked instead of waiting for keyboard input.

## Default safety posture

The baseline otherwise retains these boundaries:

- `websearch`: `allow`;
- `webfetch`: `allow`;
- unknown/non-destructive shell operations: `ask`;
- safe read-only Git operations: `allow`;
- normal file edits: `ask` unless an implementation agent overrides them to `allow`;
- sensitive file reads such as `.env`, SSH keys and AWS credentials: `ask`;
- external directories: `ask`, with explicit per-agent overrides where required;
- clearly destructive operations such as recursive deletion, force-push, hard reset/clean, Terraform/OpenTofu/Terragrunt apply/destroy, Kubernetes delete and similar operations: `deny`.
