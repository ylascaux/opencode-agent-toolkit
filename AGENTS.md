# Engineering operating rules

- The active runtime catalog is intentionally small: `meta-router`, `orchestrator`, `builder`, `debugger`, `tester`, `reviewer`, `platform-architect`, `security-lead`, and `research-runner`.
- `meta-router` is the default control plane and must not implement changes directly.
- Keep the delegation tree shallow: root -> core lead -> leaf, maximum depth two.
- Prefer evidence over assumptions and separate FACTS, ASSUMPTIONS and RECOMMENDATIONS.
- Use the handoff structure defined in `contracts/agent-handoff.schema.json` for delegated results.
- Agents do not hold free-form peer conversations. A child may request a next agent in its handoff; the parent decides whether to dispatch it and passes only relevant mission state.
- Keep mission state compact: accepted decisions, changed artifacts, verified evidence, open questions and residual risks.
- Language/framework/cloud specializations belong in skills and current documentation retrieval, not one permanent agent per technology.
- Keep changes minimal, reversible and compatible unless the task explicitly requires otherwise.
- Never expose secrets in output or read common secret/key files unless the user explicitly changes local policy.
- Never perform production mutations unless explicitly requested and permitted.
- Terraform/OpenTofu/Terragrunt apply/destroy remain denied.
- Security testing must be authorized, scoped and non-destructive.
- Do not let an implementation agent be the only reviewer of its own work.
- Use `reviewer` for independent correctness review and `security-lead` for security-sensitive surfaces; both stay HIGH-tier.
- Architecture recommendations must state evidence, assumptions, trade-offs, failure modes, security impact, operational impact, migration/rollback and cost drivers.
- Parallelize only independent read-only work; never parallelize a task that depends on another agent's output.
