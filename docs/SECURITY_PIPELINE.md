# Security pipeline

The toolkit separates security into independent perspectives to reduce correlated blind spots.

1. `threat-model` reviews design and trust boundaries before implementation.
2. `appsec` reviews application code and business logic.
3. `iac-security` reviews Terraform/Terragrunt/Kubernetes/AWS posture.
4. `supply-chain` reviews dependencies, CI, images and provenance.
5. `secrets` hunts accidental credentials without printing secret values.
6. `pentest` validates plausible findings against an explicitly authorized, non-destructive target.

Pentest safety rules: scope must be explicit; localhost/test systems are preferred; no persistence, exfiltration, DoS, credential spraying, lateral movement or stealth; stop after minimum proof.
