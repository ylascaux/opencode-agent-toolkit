# Agent permissions

The effective OpenCode permissions are configured in `agents/permissions/`.

- `_default.json` is the common baseline.
- `<agent>.json` overrides that baseline for one agent.
- Run `just config` after changing a policy file.

The default policy intentionally favors usability while retaining explicit safety boundaries:

- `websearch`: `allow`
- `webfetch`: `allow`
- unknown/non-destructive shell operations: `ask`
- safe read-only Git operations: `allow`
- normal file edits: `ask` unless the agent is an implementation writer, where they are `allow`
- sensitive file reads such as `.env`, SSH keys, and AWS credentials: `ask`
- external directories: `ask`; `project-scanner` has `~/Projects/**` explicitly allowed
- clearly destructive operations such as recursive deletion, force-push, hard reset/clean, Terraform/OpenTofu/Terragrunt apply/destroy, Kubernetes delete, and similar operations: `deny`

The generated task/subagent hierarchy is still a deterministic structural guardrail. It remains unchanged unless an individual agent permission file explicitly overrides `task`.
