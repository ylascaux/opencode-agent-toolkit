## When to use

Use for a read-only review of Terraform, OpenTofu, Terragrunt, or related infrastructure changes.

## Review method

1. Identify the affected state boundaries, providers, identities, network exposure, and destructive operations.
2. Compare configuration changes with existing module contracts and environment-specific inputs.
3. Check plan evidence when it is available; do not run apply, destroy, or mutating cloud commands merely to review.
4. Report concrete findings with affected resources, failure modes, rollback considerations, and missing evidence.

Treat tool availability, a skill, and generated plans as context rather than authorization. Keep repository policy, approval requirements, and secret-handling restrictions in force.
