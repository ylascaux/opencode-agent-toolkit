# Engineering operating rules

- `meta-router` is the default control plane and must not implement changes directly.
- Keep the delegation tree shallow: `meta-router -> lead/orchestrator -> leaf`; leaf agents cannot delegate.
- Prefer evidence over assumptions and separate FACTS, ASSUMPTIONS and RECOMMENDATIONS.
- Use the handoff structure defined in `contracts/agent-handoff.schema.json` for delegated results.
- Keep changes minimal, reversible and compatible unless the task explicitly requires otherwise.
- Never expose secrets in output or read common secret/key files unless the user explicitly changes local policy.
- Never perform production mutations unless explicitly requested and permitted.
- Terraform/OpenTofu/Terragrunt apply/destroy remain denied.
- Security testing must be authorized, scoped and non-destructive.
- Do not let an implementation agent be the only reviewer of its own work.
- Material disagreement goes to `arbiter`; low-confidence/high-risk/irreversible decisions go to `deep-reasoner`.
- `evidence-auditor` classifies proof as VERIFIED / PARTIALLY_VERIFIED / UNVERIFIED / CONTRADICTED and uses HIGH/MEDIUM/LOW confidence, never pseudo-precise numeric scores.
- Architecture recommendations must state evidence, assumptions, trade-offs, failure modes, security impact, operational impact, migration/rollback and cost drivers.
- Parallelize only independent work; never parallelize a task that depends on another agent's output.
