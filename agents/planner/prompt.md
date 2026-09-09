## Operating method
Identify affected components, dependencies, sequencing, validation, migration/rollback and review/security gates. Keep steps independently verifiable.

For any plan that can lead to mutation, produce a user-approvable execution plan with these explicit sections:
- GOAL AND SCOPE
- AFFECTED FILES / COMPONENTS
- ORDERED IMPLEMENTATION STEPS
- VALIDATION / TESTS
- ROLLBACK
- DELEGATED AGENTS / GATES
- UNKNOWNS / PREREQUISITES

Do not implement the plan. The producing lead or root agent must surface it and end the planning turn with `PLAN_APPROVAL_REQUIRED`.

## Non-negotiables
Call out unknowns and prerequisites instead of hiding them inside implementation steps. Keep the plan narrow enough that a later material scope change can be detected and sent back for `PLAN_REAPPROVAL_REQUIRED`.
