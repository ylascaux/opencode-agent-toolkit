# Engineering operating rules

- Prefer evidence over assumptions.
- Keep changes minimal and reversible.
- Never expose secrets in output.
- Never perform production mutations unless explicitly requested and permitted.
- Terraform/OpenTofu/Terragrunt apply/destroy remain denied in this toolkit.
- Security testing must be authorized, scoped and non-destructive.
- Every behavioral change should have verification evidence.
- Architecture recommendations must state assumptions, trade-offs, failure modes, security impact, operational impact and cost drivers.
