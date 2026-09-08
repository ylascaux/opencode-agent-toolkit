# OpenCode Agent Toolkit — Platform Engineering Edition

A cost-aware, evidence-driven multi-agent engineering system for OpenCode, focused on software delivery, AWS/platform architecture, Terraform/Terragrunt, Python, Go, reliability and defense-in-depth security.

## Highlights

- **37 agents** with a deliberately shallow hierarchy and per-agent model overrides.
- Provider-agnostic **LOW / MEDIUM / HIGH** model tiers.
- Default work profile: GitHub Copilot with Luna / Terra / Sol.
- Easy profile switching for personal use (for example Codex) without changing agent definitions.
- `meta-router` sees only the control/lead entry points, not every specialist.
- `review-lead` and `security-lead` select independent review/security gates.
- Leaf agents **cannot delegate** to other agents.
- Structured handoff and routing contracts under `contracts/`.
- Strong evidence gates: `arbiter`, `deep-reasoner`, `evidence-auditor`.
- Explicit web/skill policies and sensitive-file read denial for every agent.
- Reviewers may collect safe Git evidence without edit permissions.
- Enriched multi-repository architecture inventory with evidence and confidence.
- Native OpenCode V1 stable and OpenCode 2 configs generated from one source.
- Optional reversible `oc` user command lets you use the toolkit from any working directory.

## Quick start

```bash
brew install just
git clone https://github.com/ylascaux/opencode-agent-toolkit.git
cd opencode-agent-toolkit
just install
just models
just doctor

# Optional: install ~/.local/bin/oc as a symlink to the toolkit launcher.
just install-user
```

The default model profile is:

```text
LOW    -> github-copilot/gpt-5.6-luna
MEDIUM -> github-copilot/gpt-5.6-terra
HIGH   -> github-copilot/gpt-5.6-sol
```

Verify the models exposed by your GitHub Copilot account with `opencode models github-copilot`. Profile files are intentionally easy to edit when provider model IDs differ.

After `just install-user`, launch from any project while preserving that project as the OpenCode workspace:

```bash
cd ~/Projects/my-api
oc
```

The user install is intentionally minimal: it does not modify shell startup files or `~/.config`. It only creates `~/.local/bin/oc` (or another name you choose). Remove it with `just uninstall-user`.

## Model profiles

Switch the three model tiers without touching agent definitions:

```bash
just profiles
just profile copilot
just profile codex
just models
```

The mapping from agents to tiers is stored in `profiles/agent-tiers.json`. Concrete provider models live in `profiles/*.env.example`.

Persistent per-agent overrides belong in `.env.local`, which profile switching never modifies:

```bash
MODEL_BUILDER=openai/gpt-5.3-codex
MODEL_REVIEWER=github-copilot/gpt-5.6-sol
```

Resolution order is:

```text
MODEL_<AGENT> override
        ↓
agent LOW / MEDIUM / HIGH tier
        ↓
active provider profile
```

`just configure` / `just configure-litellm` remain available only as optional future LiteLLM discovery helpers; LiteLLM is not required for the default setup.

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
just profile copilot
just profiles
just models
just install-user
just user-status
just uninstall-user
just doctor
just run
just v1
just v2
just check
just test
just scan
just api
just refresh
just clean
```

Use a different command name if `oc` already exists:

```bash
just install-user opencode-agents
```

Override the user bin directory without changing shell configuration:

```bash
OPENCODE_TOOLKIT_BIN_DIR="$HOME/bin" just install-user
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
