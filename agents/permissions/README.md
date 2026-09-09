# Per-agent permissions

Permissions are intentionally editable without touching the Python generator.

- `_default.json` is the common baseline applied to every agent.
- `<agent>.json` is the override for one agent.
- Agent overrides win over `_default.json`.
- The generated task/subagent topology remains in place unless an agent file explicitly overrides `task`.
- `websearch` and `webfetch` are allowed by default for every agent.
- Safe repository inspection is allowed by default, including read-only Git commands.
- Unknown/non-destructive shell operations default to `ask` rather than `deny`.
- Sensitive file reads default to `ask` rather than `deny`.
- Clearly destructive operations remain `deny` by default (for example force-push, hard reset/clean, recursive deletion, Terraform/OpenTofu/Terragrunt apply/destroy, Kubernetes delete, and similar destructive cloud commands).

## Example

To let `aws-platform` run an additional command without prompting, edit `agents/permissions/aws-platform.json`:

```json
{
  "bash": {
    "aws sts get-caller-identity*": "allow"
  }
}
```

To change a tool permission for only one agent:

```json
{
  "edit": "allow",
  "webfetch": "allow",
  "task": {
    "*": "ask"
  }
}
```

Run `just config` after changing a permission file. `just install`, `just preflight`, and normal toolkit startup also regenerate and apply these policies.
