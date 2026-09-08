# OpenCode Agent Toolkit — Platform Engineering Edition

A cost-aware, evidence-driven multi-agent engineering system for OpenCode, focused on software delivery, AWS/platform architecture, Terraform/Terragrunt, Python, Go, reliability and defense-in-depth security.

## Highlights

- **37 independently configurable agents** with a deliberately shallow hierarchy.
- `meta-router` sees only the control/lead entry points, not every specialist.
- `review-lead` and `security-lead` select independent review/security gates.
- Leaf agents **cannot delegate** to other agents.
- Structured handoff and routing contracts under `contracts/`.
- Strong evidence gates: `arbiter`, `deep-reasoner`, `evidence-auditor`.
- Explicit web/skill policies and sensitive-file read denial for every agent.
- Reviewers may collect safe Git evidence without edit permissions.
- Enriched multi-repository architecture inventory with evidence and confidence.
- Native OpenCode V1 stable and OpenCode 2 configs generated from one source.
- `just configure` discovers LiteLLM models and maps profiles to all agents.

## Quick start

```bash
brew install just
git clone https://github.com/ylascaux/opencode-agent-toolkit.git
cd opencode-agent-toolkit
just install

# Optional but recommended: discover your LiteLLM models and specialize agent routing.
export LITELLM_BASE_URL="https://gateway.example.com"
export LITELLM_API_KEY="..."
just configure

just doctor
just run
```

Cloudflare Access is supported for model discovery via `CF_ACCESS_TOKEN` or `LITELLM_HEADERS_JSON`; credentials are never written by the configurator.

## Control plane

```text
User
 |
 v
meta-router
 |-- orchestrator --------> delivery/domain leaves
 |-- review-lead ---------> independent review leaves
 |-- platform-architect --> architecture/platform leaves
 |-- security-lead -------> security leaves
 |-- arbiter
 |-- deep-reasoner
 `-- evidence-auditor
```

Maximum intended delegation depth stays at **2**. Leads cannot invoke other leads.

## Commands

```text
/auto <task>
/ship <feature/fix>
/review <change>
/architecture <need>
/security <scope>
/debug <problem>
/incident <incident>
/cost <scope>
```

## Just recipes

```bash
just install
just configure
just doctor
just run
just v1
just v2
just check
just test
just scan
just api
just models
just refresh
just clean
```

## Documentation

- English: [`docs/en/`](docs/en/README.md)
- Français: [`docs/fr/`](docs/fr/README.md)

## Safety defaults

- Terraform/OpenTofu/Terragrunt `apply` and `destroy` are denied.
- Leaf agents cannot launch subagents.
- Common `.env`, key, SSH and AWS credential paths are denied to all agent file readers.
- Pentesting is explicitly authorized, scoped and non-destructive only.
- Review/security agents do not modify code.
- High-risk or low-confidence work escalates instead of being silently accepted.

## Validate

```bash
just check
```

## License

MIT.
