# Security pipeline

Security is a separate review pipeline, not a flag on the builder.

```text
meta-router
  -> security-lead
       -> threat-model
       -> appsec
       -> iac-security
       -> supply-chain
       -> secrets
       -> pentest
```

`security-lead` selects only gates relevant to the actual attack surface.

- `threat-model`: assets, actors, entry points, trust boundaries and abuse cases.
- `appsec`: authn/authz, injection, SSRF, traversal, deserialization, XSS/CSRF, uploads, crypto, rate limits and business logic.
- `iac-security`: IAM, public exposure, encryption/KMS, policies, workload identity/RBAC, state and logging.
- `supply-chain`: dependencies, lockfiles, CI actions, images, provenance and version-specific vulnerability evidence.
- `secrets`: credential/sensitive-value exposure with redacted output.
- `pentest`: runtime validation only for explicitly authorized, scoped targets.

Pentest never performs persistence, exfiltration, DoS, credential spraying, lateral movement, stealth or destructive changes.

## Tool policy

Security review agents do not edit code. Security tools and web access require explicit policy/approval; secrets and pentest have web disabled by default. All agents deny common `.env`, key, SSH and AWS credential paths.

## Finding contract

Each finding carries severity, confidence, direct evidence, exploitability/preconditions, impact, remediation and verification. Exploitable vulnerabilities are distinguished from hardening guidance.
