set shell := ["bash", "-cu"]

# Show available recipes.
default:
    @just --list

# First-time setup: .env + Python environment + validation.
install:
    bash ./scripts/bootstrap

# Check local prerequisites and configuration without changing anything.
doctor:
    bash ./scripts/doctor

# Validate both OpenCode configs and agent/model parity.
check: config test

config:
    python3 ./scripts/generate-config
    python3 -m json.tool opencode.jsonc >/dev/null
    python3 -m json.tool opencode.v2.jsonc >/dev/null
    @echo "OpenCode V1/V2 configs: generated and valid JSON"

# Run the repository test suite.
test:
    python3 -m unittest discover -s tests -v

# Launch using OPENCODE_MAJOR from .env.
run *args:
    bash ./scripts/opencode-agents {{args}}

# Force OpenCode V1 stable for this invocation.
v1 *args:
    OPENCODE_MAJOR=1 bash ./scripts/opencode-agents {{args}}

# Force OpenCode 2 beta for this invocation.
v2 *args:
    OPENCODE_MAJOR=2 bash ./scripts/opencode-agents {{args}}

# Generate the normalized project architecture inventory.
scan *args:
    bash ./scripts/scan-projects {{args}} > architecture-inventory.json
    @echo "Wrote architecture-inventory.json"

# Start the local project inventory API on 127.0.0.1:8765 by default.
api:
    bash ./scripts/inventory-api

# Print all configured MODEL_* mappings from .env without evaluating secrets.
models:
    @grep '^MODEL_' .env 2>/dev/null || { echo "Missing .env; run: just install" >&2; exit 1; }

# Re-run bootstrap after changing requirements or local configuration.
refresh:
    bash ./scripts/bootstrap --refresh

# Remove generated local state only.
clean:
    rm -rf .venv architecture-inventory.json security-findings.json
