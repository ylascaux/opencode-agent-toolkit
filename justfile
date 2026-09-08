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

# Install a reversible per-user command (default: oc) and the inert-unless-enabled runtime watchdog plugin.
install-user command="oc":
    bash ./scripts/user-link install "{{command}}"

# Remove the per-user command and watchdog only when they point to this toolkit.
uninstall-user command="oc":
    bash ./scripts/user-link uninstall "{{command}}"

# Show whether the per-user command and runtime watchdog point to this toolkit.
user-status command="oc":
    bash ./scripts/user-link status "{{command}}"

# Optional/future: discover LiteLLM models and create explicit per-agent mappings.
configure *args:
    python3 ./scripts/configure-models {{args}}

configure-litellm *args:
    python3 ./scripts/configure-models {{args}}

doctor:
    bash ./scripts/doctor

check: config test

config:
    python3 ./scripts/generate-config
    python3 ./scripts/apply-runtime-policy
    python3 -m json.tool opencode.jsonc >/dev/null
    python3 -m json.tool opencode.v2.jsonc >/dev/null
    @echo "OpenCode V1/V2 configs: generated, runtime-bounded and valid JSON"

test:
    python3 -m unittest discover -s tests -v

# Run zero-token checks without starting an OpenCode session.
preflight major="1":
    @test -f .env || { echo "Missing .env; run: just install" >&2; exit 1; }; set -a; source .env; [[ -f .env.local ]] && source .env.local; set +a; eval "$(python3 ./scripts/resolve-models)"; python3 ./scripts/generate-config >/dev/null; python3 ./scripts/apply-runtime-policy >/dev/null; if [[ "{{major}}" == "2" ]]; then bin="${OPENCODE_BIN:-opencode2}"; else bin="${OPENCODE_BIN:-opencode}"; fi; python3 ./scripts/preflight --bin "$bin" --major "{{major}}"

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
    rm -rf .venv architecture-inventory.json security-findings.json
