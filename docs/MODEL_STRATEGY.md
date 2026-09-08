# Model strategy

Every agent maps to its own `MODEL_*` variable. A practical strategy is:

- strongest reasoning model: orchestrator, platform-architect, architecture-designer, threat-model, complex debugger;
- strong coding model: builder, Terraform, Python, Go, Kubernetes, AppSec;
- fast/cheap model: scanner, mocks, docs, first-pass tests, FinOps/observability inventory;
- independent reviewer model family when possible: reviewer/security agents should not always use the same model as the builder.

This deliberately avoids hard-coding vendor names. Your LiteLLM gateway can change routing without modifying agent definitions.
