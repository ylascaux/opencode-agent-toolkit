# Usage

For repository-local use, start with `just run`. For daily use from any workspace, install the reversible user command once with `just install-user`, then launch with `oc` from the project you want OpenCode to work on.

```bash
cd ~/Projects/my-api
oc
```

The launcher preserves the current working directory. The toolkit repository supplies the generated OpenCode config and model mappings; the directory from which you run `oc` remains the OpenCode workspace.

Use `/auto` when routing should be decided automatically.

## Plan approval

The default runtime policy is `PLAN_APPROVAL_MODE=changes`. Read-only discovery and analysis can run immediately, but the toolkit must show a concrete plan and wait for explicit approval before it mutates files, repository state, infrastructure, configuration, or another external system.

A normal change therefore looks like this:

```text
/ship Add idempotency to this event consumer.
```

OpenCode gathers the minimum evidence needed to plan, then returns a plan ending with:

```text
PLAN_APPROVAL_REQUIRED
```

Reply with a short explicit approval such as `go`, `approve`, `oui`, or `valide` to execute that plan. Replying with anything else is treated as new/changed scope and requires a revised plan. `reject`, `non`, `stop`, or `annule` rejects the current plan.

You can request planning without execution explicitly:

```text
/plan Add idempotency to this event consumer.
```

If implementation discovers a material scope/dependency/trust-boundary/destructive-step/rollback change, execution stops and the revised plan ends with:

```text
PLAN_REAPPROVAL_REQUIRED
```

Approval is scoped to the current root request and its child agents. A later user request resets the approval automatically.

Configure the behavior in `.env` or `.env.local`:

```bash
PLAN_APPROVAL_MODE=changes   # default
# PLAN_APPROVAL_MODE=off     # disable the gate
# PLAN_APPROVAL_MODE=always  # also gate delegated execution beyond direct discovery
```

The plan boundary is enforced by runtime plugins for both OpenCode V1 and V2. Agent prompts improve the workflow, but a mutating tool is still blocked when no approved plan exists.

## Delivery

```text
/ship Add idempotency to this event consumer.
```

The meta-router delegates planning to `orchestrator`, which selects the implementation/test/review/security leaves. The plan is surfaced to the root user before implementation starts. After approval, the orchestrator executes only the approved scope. The implementation agent never self-approves.

## Review

```text
/review Review the current branch before merge.
```

This goes through `review-lead`, which selects only relevant review dimensions. Pure read-only review does not require a plan approval.

## Architecture

```text
/architecture Discover the systems under ~/Projects and propose a target AWS platform architecture.
```

The workflow is staged rather than self-reviewed:

1. `meta-router` routes design and evidence gathering to `platform-architect`.
2. If a durable document or other artifact will be created/updated, the stable write/migration plan is surfaced for user approval first.
3. After approval, `platform-architect` delegates file writing to `docs-writer` once the design is stable.
4. Once the artifact exists, `meta-router` routes it to `review-lead` for an independent repository-backed review.
5. When trust boundaries, IAM, public exposure, secrets or infrastructure-security posture materially change, `security-lead` runs as an additional gate. It can run in parallel with `review-lead` when both only read the completed artifact.
6. The final synthesis reports evidence, trade-offs, rejected alternatives, migration/rollback and residual risks.

The producing architecture path does not perform its own final independent review.

To review an existing architecture artifact without running a new design pass first:

```text
/architecture-review Review docs/architecture/aws-platform.md against the current repository.
```

This routes through `review-lead`, which can re-establish facts with `project-scanner` and select only the relevant platform/security dimensions.

## Security

```text
/security Review the authentication and Terraform changes on this branch.
```

This goes to `security-lead`. Runtime pentesting is used only when an authorized target is explicit.

## Evidence handoff

Delegated agents end with STATUS, SUMMARY, FACTS, ASSUMPTIONS, EVIDENCE, FINDINGS, RESIDUAL RISKS, RECOMMENDED NEXT AGENTS and categorical CONFIDENCE. HIGH means directly verified/reproduced; MEDIUM means strong static/indirect evidence; LOW means unresolved hypothesis or missing proof.

## Model profiles

The default work profile is GitHub Copilot with Luna/Terra/Sol mapped to LOW/MEDIUM/HIGH tiers.

```bash
just models
just profile copilot
just profile codex
```

Use `.env.local` for persistent per-agent overrides:

```bash
MODEL_BUILDER=openai/gpt-5.3-codex
```

The active profile decides only the concrete tier models; agent routing, permissions and safety policies remain unchanged.

## User command lifecycle

```bash
just install-user      # creates ~/.local/bin/oc
just user-status       # verifies the link
just uninstall-user    # removes it only if owned by this toolkit
```

Choose another command name when needed:

```bash
just install-user opencode-agents
```
