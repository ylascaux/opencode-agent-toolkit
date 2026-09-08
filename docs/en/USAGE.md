# Usage

For repository-local use, start with `just run`. For daily use from any workspace, install the reversible user command once with `just install-user`, then launch with `oc` from the project you want OpenCode to work on.

```bash
cd ~/Projects/my-api
oc
```

The launcher preserves the current working directory. The toolkit repository supplies the generated OpenCode config and model mappings; the directory from which you run `oc` remains the OpenCode workspace.

Use `/auto` when routing should be decided automatically.

## Delivery

```text
/ship Add idempotency to this event consumer.
```

The meta-router delegates to `orchestrator`; the orchestrator selects implementation/test/review/security leaves. The implementation agent never self-approves.

## Review

```text
/review Review the current branch before merge.
```

This goes through `review-lead`, which selects only relevant review dimensions.

## Architecture

```text
/architecture Discover the systems under ~/Projects and propose a target AWS platform architecture.
```

The workflow is staged rather than self-reviewed:

1. `meta-router` routes design and evidence gathering to `platform-architect`.
2. If a durable document is requested, `platform-architect` delegates file writing to `docs-writer` after the design is stable.
3. Once the artifact exists, `meta-router` routes it to `review-lead` for an independent repository-backed review.
4. When trust boundaries, IAM, public exposure, secrets or infrastructure-security posture materially change, `security-lead` runs as an additional gate. It can run in parallel with `review-lead` when both only read the completed artifact.
5. The final synthesis reports evidence, trade-offs, rejected alternatives, migration/rollback and residual risks.

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
