# Routing and model strategy

## Minimum-sufficient routing

The router optimizes for the cheapest sufficient path, not the smallest model at any cost. Risk, uncertainty and blast radius override cost optimization.

Suggested policy:

| Situation | Route |
|---|---|
| Low complexity + low risk | One narrow specialist |
| Medium behavioral change | Specialist + tester + reviewer |
| Multi-domain / migration / high blast radius | Orchestrator + relevant specialists |
| New trust boundary | Add threat-model and relevant security gates |
| Material disagreement | Add arbiter |
| High risk / low confidence / irreversible decision | Add deep-reasoner |
| Non-trivial completion | Add evidence-auditor |

Independent read-only analyses can run in parallel when the runtime supports it. Tasks with true dependencies should remain sequential.

## Confidence

Final decisions should expose a confidence level:

- `high`: direct evidence supports the conclusion and relevant gates passed;
- `medium`: conclusion is likely correct but some evidence is indirect or assumptions remain;
- `low`: meaningful uncertainty, missing evidence or unresolved disagreement remains.

Low confidence on high-impact work should trigger escalation instead of silent acceptance.

## Model tiers

A practical model strategy is:

- **Fast/cheap**: scanning, mocks, docs, simple classification and repetitive transforms.
- **Strong coding**: builder, Python, Go, Terraform, CI/CD, Kubernetes.
- **Strong reasoning**: orchestrator, architecture, reviewer, threat model, AppSec.
- **Deep reasoning**: only `deep-reasoner`, difficult arbitration, major migrations or critical architecture.

Every agent maps to a dedicated `MODEL_*` variable, so LiteLLM can provide the actual routing implementation.

## Independent model families

When possible, do not use the same model family for both implementation and independent approval. A coding model can build while a different reasoning/security model reviews it. This reduces correlated blind spots.

## Smart Router integration

The default `.env.example` points every agent at `litellm/smart-router`, so the toolkit works without hard-coded vendor choices. You can later pin only critical roles to explicit model groups while leaving routine roles on Smart Router.
