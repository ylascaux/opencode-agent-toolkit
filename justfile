set shell := ["bash", "-cu"]

default:
    @just --list

# First-time setup: .env + Python environment + config generation + tests.
install:
    bash ./scripts/bootstrap

# Apply a model-provider profile (default: copilot). Persistent per-agent overrides belong in .env.local.
profile name="copilot":
    python3 ./scripts/apply-profile "{{name}}"

# List available model profiles.
profiles:
    @for f in profiles/*.env.example; do basename "$f" .env.example; done

# List discovered agents from agents/<name>/.
agents:
    python3 ./scripts/agent_config.py

# Scaffold a new self-contained agent directory.
new-agent name *args:
    python3 ./scripts/new-agent "{{name}}" {{args}}

# Install a reversible per-user command (default: oc) in ~/.local/bin.
install-user command="oc":
    bash ./scripts/user-link install "{{command}}"

# Remove the per-user command only when it points to this toolkit.
uninstall-user command="oc":
    bash ./scripts/user-link uninstall "{{command}}"

# Show whether the per-user command points to this toolkit.
user-status command="oc":
    bash ./scripts/user-link status "{{command}}"

# Optional only: discover LiteLLM models and create explicit per-agent mappings.
# This command is never invoked by `just config`.
configure-litellm *args:
    python3 ./scripts/configure-models {{args}}

doctor:
    bash ./scripts/doctor

# Fast deterministic checks performed before an OpenCode run.
preflight:
    @test -f .env || { echo "Missing .env; run: just install" >&2; exit 1; }; set -a; source .env; [[ -f .env.local ]] && source .env.local; set +a; python3 ./scripts/generate-config >/dev/null; python3 ./scripts/apply-reliability >/dev/null; bash ./scripts/preflight

# Show the effective reliability policy after environment overrides.
reliability:
    @test -f .env || { echo "Missing .env; run: just install" >&2; exit 1; }; set -a; source .env; [[ -f .env.local ]] && source .env.local; set +a; python3 ./scripts/show-reliability

check: config test runtime-test

# Purely local/deterministic generation. No provider discovery and no interactive prompts.
config:
    python3 ./scripts/generate-config
    python3 ./scripts/apply-reliability
    python3 -m json.tool opencode.jsonc >/dev/null
    python3 -m json.tool opencode.v2.jsonc >/dev/null
    @echo "OpenCode V1/V2 configs: generated, reliability-capped and valid JSON"

test:
    python3 -m unittest discover -s tests -v

# Behavioral tests for queue/call tracking, progress-aware loop detection,
# provider retry decisions, cost enforcement, permission/stall handling,
# and non-interactive shell invariants.
runtime-test:
    node --test tests/*.test.mjs

run *args:
    bash ./scripts/opencode-agents {{args}}

v1 *args:
    OPENCODE_MAJOR=1 bash ./scripts/opencode-agents {{args}}

v2 *args:
    OPENCODE_MAJOR=2 bash ./scripts/opencode-agents {{args}}

scan *args:
    bash ./scripts/scan-projects {{args}} > architecture-inventory.json
    @echo "Wrote architecture-inventory.json"

api:
    bash ./scripts/inventory-api

models:
    @test -f .env || { echo "Missing .env; run: just install" >&2; exit 1; }; set -a; source .env; [[ -f .env.local ]] && source .env.local; set +a; python3 ./scripts/resolve-models --show

refresh:
    bash ./scripts/bootstrap --refresh

clean:
    rm -rf .venv .generated architecture-inventory.json security-findings.json
