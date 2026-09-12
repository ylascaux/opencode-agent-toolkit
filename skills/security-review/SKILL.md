## When to use

Use for a defensive review of a defined code, configuration, dependency, or infrastructure change.

## Review method

1. Establish the changed trust boundaries, data flows, identities, and externally reachable surfaces.
2. Check authentication, authorization, input handling, secret exposure, dependency changes, and logging appropriate to that scope.
3. Separate verified findings from assumptions and state the evidence needed to resolve uncertainty.
4. Rank actionable findings by impact and exploitability, including practical remediation and rollback considerations.

This is a non-destructive review aid. It does not authorize scanning outside the user-approved scope, accessing credentials, or bypassing repository security controls.
