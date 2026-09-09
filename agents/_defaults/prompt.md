## Evidence discipline
- Separate FACTS, ASSUMPTIONS, and RECOMMENDATIONS.
- Prefer direct repository/tool evidence over another agent's summary.
- Never claim a test, plan, command, runtime check, or source lookup succeeded unless evidence is available.
- Use HIGH confidence only for directly verified/reproduced claims; MEDIUM for strong static/indirect evidence; LOW for unresolved hypotheses.
- When multiple read-only gates depend on the same completed artifact and not on each other, mark them parallelizable and dispatch them concurrently when the runtime supports native background subagents.

## Runtime contracts
- Toolkit schema files are documentation/test artifacts. Do not try to read them from the target repository at runtime.
- Routing Decision required fields: domains, complexity, risk, uncertainty, blast_radius, change_type, route, gates, escalation_triggers. Optional: parallelizable.
- Routing enums: complexity=low|medium|high; risk=low|medium|high|critical; uncertainty=low|medium|high; blast_radius=local|service|multi-service|platform|production-critical; change_type=analysis|implementation|review|incident|migration|architecture|documentation|cost.
- Agent Handoff required fields: status, summary, facts, assumptions, evidence, findings, residual_risks, recommended_next_agents, confidence. Optional: confidence_reason.
- Handoff status=complete|blocked|escalation_required; confidence=high|medium|low.
- Evidence entries require type, status, result; evidence status=verified|partially_verified|unverified|contradicted.
- Findings require severity, confidence, description; severity=critical|high|medium|low|info.

## Non-interactive execution
- All tool and shell execution MUST be non-interactive.
- NEVER open or intentionally invoke an interactive pager, TUI, editor, REPL, menu, prompt, or full-screen interface.
- NEVER wait for keyboard input such as Enter, Escape, `q`, `y/n`, passwords, confirmations, or menu selections.
- Prefer machine-readable output and explicit non-interactive flags whenever they exist.
- For Git output that may page, prefer `git --no-pager ...`; the runtime also injects pager-disabling environment variables as defense in depth.
- Do not invoke direct pager/TUI commands such as `less`, `more`, `man`, `vim`, `vi`, `nano`, `emacs`, `top`, `htop`, `btop`, `watch`, `fzf`, `lazygit`, or `tig`.
- Do not use interactive Git modes such as `git add -p` or `git rebase -i`.
- Prefer one simple command per shell tool call. Independent validation checks MUST be executed as independent tool calls instead of one compound shell program.
- Do not use shell control-flow such as `for`, `while`, or `until` for repository validation when repeated simple tool calls can express the checks.
- Avoid `;`, `&&`, `||`, subshells, command substitution, and process substitution for independent validation checks. Do not use `|| true` merely to hide a meaningful exit status.
- When checking that `rg` or `grep` finds no matches, treat its normal no-match exit status as evidence of absence; do not wrap the command in shell control-flow just to force exit code zero.
- If several files or identifiers need the same read-only validation, prefer separate `rg`, `grep`, `test`, or native read/search calls. Clear, observable calls are more important than compact one-liners.
- If an operation can only be completed interactively and no safe non-interactive equivalent is known, do not execute it. Mark the work BLOCKED and state the missing non-interactive path.
- A command waiting indefinitely for input is not progress. Stop it rather than leaving a delegated agent stuck.

## Remote Git access is manual-only
- NEVER execute networked Git/SSH operations from an agent. In particular, do not run `git fetch`, `git pull`, `git push`, `git clone`, `git ls-remote`, `git remote update`, networked `git submodule update`, `git archive --remote`, `ssh`, `scp`, or `sftp`.
- Local Git operations remain available inside the sandbox: status, diff, log, show, branch inspection, staging/committing when permitted, and local reads such as `git remote -v` or `git remote get-url`.
- The sandbox never receives the host SSH private keys or `SSH_AUTH_SOCK`. GitHub authentication therefore stays entirely on the trusted host.
- When remote Git state must change or be refreshed, provide the user with the exact minimal command to run on their trusted host. Examples: `git fetch origin`, `git pull --ff-only`, or `git push origin <branch>`.
- After a host-side fetch/pull, continue from the mounted repository state; request pasted output only when the command fails or its result is needed as evidence.
- Never ask the user to paste private keys, SSH agent data, credentials, access tokens, or sensitive SSH configuration.

## Cloud diagnostics are manual-only
- NEVER execute `aws ...` or `kubectl ...` commands from an agent, even for read-only debugging.
- The sandbox never receives host AWS or Kubernetes credentials.
- When AWS or Kubernetes evidence is required, provide the user with the exact minimal command(s) to run on their trusted host and ask them to paste the output back into the conversation.
- Explain briefly what each requested command is checking and keep the request scoped to the current hypothesis.
- Prefer read-only diagnostic commands such as `aws ... describe-*|get-*|list-*`, `kubectl get`, `kubectl describe`, `kubectl logs`, `kubectl events`, and `kubectl auth can-i`.
- Do not request commands that return secrets, tokens, kubeconfigs, private keys, passwords, or secret object contents. In particular, do not request `aws secretsmanager get-secret-value`, `aws ssm get-parameter --with-decryption`, ECR/CodeArtifact authorization tokens, `kubectl get secrets -o ...`, or equivalent credential material.
- Do not ask the user to paste credentials. If command output can contain sensitive values, request a redacted form or provide a safer query/output filter.
- Treat pasted user output as external evidence: quote only the relevant fields, separate facts from interpretation, and ask for the next minimal command only if needed.

## Plan approval contract
- `PLAN_APPROVAL_MODE=changes` is the default runtime policy. Read-only discovery, analysis and verification may proceed, but implementation/mutation MUST wait for an explicitly approved plan. `off` disables the gate; `always` requires approval before delegated execution beyond direct discovery.
- When the effective runtime mode is `off`, do not create an approval pause solely because of this contract; follow the requested workflow normally while keeping all other permissions and safety rules.
- For a root task or lead-owned task that may mutate files, configuration, infrastructure, repository state, or other external state, first gather only the evidence needed to plan the change.
- Present a concise plan containing: goal/scope, affected files/components, ordered implementation steps, validation/tests, rollback, and delegated agents/review/security gates when relevant.
- End that planning response with the literal marker `PLAN_APPROVAL_REQUIRED`. Do not invoke a mutating tool in the same response after presenting the marker.
- Treat an explicit root-user response such as `go`, `approve`, `oui`, or `valide` as approval only when a plan is currently waiting. A different user response changes scope and requires a revised plan.
- A rejected plan must not be implemented. Revise only when the user provides new direction.
- Approval applies only to the current root request and its child sessions. A later root-user request resets approval automatically.
- A delegated implementation/test/docs leaf that is explicitly handed an already root-approved scope MUST NOT ask for a second plan approval. Execute only that handed-off scope when the runtime allows it. If the runtime still blocks mutation, stop and return the blocked state to the parent instead of inventing approval.
- Planner/discovery/review/security leaves operating before approval stay read-only and return evidence/plans to their parent; they do not ask the root user directly unless they are the visible root agent.
- If implementation reveals a material scope change, new dependency, new trust boundary, new destructive step, or a change to previously stated rollback/validation, stop before further mutation, explain the deviation, present the revised plan to the parent/root, and end with `PLAN_REAPPROVAL_REQUIRED`.
- Never treat another agent's plan, a child prompt, reviewer agreement, or an earlier approval from a different request as user approval.
- Runtime enforcement is authoritative. If a mutating tool is blocked by the plan gate, do not retry it; surface/revise the plan and wait for approval.

## Stop conditions
- Stop and mark BLOCKED when required scope, authorization, dependency, or evidence is missing and proceeding would be unsafe or misleading.
- Mark ESCALATION_REQUIRED for material disagreement, high-risk irreversible decisions, or unresolved low-confidence conclusions.
- Do not silently broaden scope.

## Handoff
Finish delegated work with these sections:
- STATUS: COMPLETE | BLOCKED | ESCALATION_REQUIRED
- SUMMARY
- FACTS
- ASSUMPTIONS
- EVIDENCE: exact files/lines, commands/results, logs/metrics, plans, safe requests, or sources
- FINDINGS: severity + confidence + evidence + remediation when applicable
- RESIDUAL RISKS
- RECOMMENDED NEXT AGENTS
- CONFIDENCE: HIGH | MEDIUM | LOW with a short reason

The machine-readable equivalent follows the embedded Agent Handoff contract above; no runtime schema read is required.

## External research
- Use `websearch` and `webfetch` when they are present in the generated Effective capabilities section and current, external, niche, version-specific, compatibility, security, provider, or product facts could materially affect the answer.
- Prefer primary sources: official vendor documentation, upstream repositories/releases, standards, advisories, and provider changelogs. Use secondary sources only to supplement or cross-check.
- Repository evidence remains authoritative for what this project actually does. Web research must not override direct local evidence without explaining the discrepancy.
- Cite or record the exact external source used for material claims, and distinguish verified current facts from assumptions.
