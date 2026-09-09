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

# Install the dedicated OpenCode 2 beta launcher as ~/.local/bin/oc2.
install-oc2:
    bash ./scripts/user-link install oc2

# Remove the per-user command only when it points to this toolkit.
uninstall-user command="oc":
    bash ./scripts/user-link uninstall "{{command}}"

# Remove the dedicated OpenCode 2 beta launcher.
uninstall-oc2:
    bash ./scripts/user-link uninstall oc2

# Show whether the per-user command points to this toolkit.
user-status command="oc":
    bash ./scripts/user-link status "{{command}}"

# Show whether the OpenCode 2 beta launcher is installed.
oc2-status:
    bash ./scripts/user-link status oc2

# Optional only: discover LiteLLM models and create explicit per-agent mappings.
# This command is never invoked by `just config`.
configure-litellm *args:
    python3 ./scripts/configure-models {{args}}

doctor:
    bash ./scripts/doctor

# Build the hardened Nix development sandbox image using Docker or Podman.
sandbox-build:
    bash ./scripts/sandbox-build

# Enable sandboxed agent shell execution persistently in .env.local.
sandbox-on: sandbox-build
    python3 ./scripts/sandbox-toggle on
    @echo "Sandbox enabled. AWS, kubectl and remote Git remain manual-only on the trusted host."

# Disable sandboxed shell execution without deleting the image.
sandbox-off:
    python3 ./scripts/sandbox-toggle off

# Validate sandbox policy, cloud command filtering and the local container runtime/image.
sandbox-doctor:
    bash ./scripts/sandbox-doctor

# Remove orphaned toolkit sandbox containers. Does not remove the image.
sandbox-clean:
    @engine="$${OAT_SANDBOX_ENGINE:-auto}"; if [[ "$$engine" == auto ]]; then if command -v docker >/dev/null 2>&1; then engine=docker; elif command -v podman >/dev/null 2>&1; then engine=podman; else echo "docker/podman not found" >&2; exit 0; fi; fi; ids="$$($$engine ps -aq --filter label=opencode-agent-toolkit=1)"; if [[ -n "$$ids" ]]; then $$engine rm -f $$ids; else echo "No orphaned toolkit sandboxes"; fi

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

# Start a headless OpenCode server with the active toolkit version/config.
serve *args:
    bash ./scripts/opencode-agents serve {{args}}

# Start a headless OpenCode 2 server explicitly.
serve-v2 *args:
    OPENCODE_MAJOR=2 bash ./scripts/opencode-agents serve {{args}}

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
