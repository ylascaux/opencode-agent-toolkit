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
- If an operation can only be completed interactively and no safe non-interactive equivalent is known, do not execute it. Mark the work BLOCKED and state the missing non-interactive path.
- A command waiting indefinitely for input is not progress. Stop it rather than leaving a delegated agent stuck.

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
