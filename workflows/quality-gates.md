# Quality gates

## Standard code change
planner → specialist/builder → tester → reviewer

## Security-sensitive code change
planner → threat-model → specialist/builder → tester → appsec → reviewer → pentest (only when an authorized runnable target exists)

## Infrastructure change
project-scanner (optional) → platform-architect → aws-platform/kubernetes → terraform-terragrunt → iac-security → sre → observability → finops → reviewer

## Dependency / CI change
cicd → supply-chain → secrets → reviewer

The orchestrator owns deduplication and final acceptance. High-severity unresolved security findings block completion unless the user explicitly accepts the risk.
