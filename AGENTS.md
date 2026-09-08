# Engineering operating rules

- `meta-router` is the default control plane: prefer the minimum sufficient route and escalate only when justified.
- Prefer evidence over assumptions and separate facts from hypotheses.
- Keep changes minimal, reversible and compatible unless the task explicitly requires otherwise.
- Never expose secrets in output.
- Never perform production mutations unless explicitly requested and permitted.
- Terraform/OpenTofu/Terragrunt apply/destroy remain denied in this toolkit.
- Security testing must be authorized, scoped and non-destructive.
- Do not let an implementation agent be the only reviewer of its own work.
- Material disagreements should be sent to `arbiter`; low-confidence/high-risk decisions should be sent to `deep-reasoner`.
- Every non-trivial behavioral change should have verification evidence. Use `evidence-auditor` for high-risk or ambiguous completion claims.
- Architecture recommendations must state assumptions, trade-offs, failure modes, security impact, operational impact, migration/rollback and cost drivers.
- Prefer parallel independent reviews when supported, but never parallelize tasks with a true dependency on another agent's output.
