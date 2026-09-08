# Security pipeline

Security is a separate review plane so that the agent producing a change is not the only agent judging its security.

## Gates

1. `threat-model`: assets, actors, entry points, trust boundaries, abuse cases and mitigations.
2. `appsec`: authentication/authorization, injection, SSRF, path traversal, deserialization, XSS/CSRF, uploads, redirects, sensitive data, crypto and business logic.
3. `iac-security`: IAM, public exposure, encryption, KMS, security groups, bucket policies, logging, workload identity, Kubernetes RBAC/pod privilege and Terraform state security.
4. `supply-chain`: dependency risk, lockfiles, CI permissions, image provenance, action pinning and build integrity.
5. `secrets`: accidental credentials or sensitive material; values must be redacted.
6. `pentest`: authorized runtime validation of plausible findings using the least invasive proof necessary.

## Adaptive selection

Not every change runs every gate. The router selects the relevant controls based on attack surface. Examples:

- new API/auth flow: threat-model + AppSec;
- Terraform/EKS change: threat-model when trust changes + IaC security;
- dependency or CI change: supply-chain;
- suspected credential leak: secrets;
- runtime exploitability question: pentest only when the target is explicitly authorized.

## Pentest safety

The pentest agent must have explicit scope. Prefer localhost, test environments or provided fixtures. It must not persist access, exfiltrate data, perform denial of service, credential spraying, lateral movement, stealth or destructive actions. Stop once minimum proof is sufficient.

The default permissions allow harmless localhost `curl` checks; other shell commands require approval.

## Finding quality

Security findings should contain:

- affected component/location;
- evidence;
- exploitability conditions;
- impact;
- severity and confidence;
- remediation;
- verification steps;
- residual risk.

Hardening suggestions should be separated from exploitable vulnerabilities.

## Terraform safety

Terraform/OpenTofu/Terragrunt formatting and validation can be allowed automatically; plans require approval; `apply` and `destroy` are denied by default.
