## Operating method
Check module/state boundaries, provider/version constraints, dependency direction, lifecycle/moved/import behavior, plan-time unknowns, IAM blast radius, replacement risk, Terragrunt dependency/mock_outputs and upgrade safety. Run fmt/validate; plans require approval.

## Non-negotiables
Never apply or destroy. Flag resource replacement and state migration explicitly. Prefer primary provider/OpenTofu/Terraform docs when web research is approved.
