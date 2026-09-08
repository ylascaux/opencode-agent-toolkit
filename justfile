set shell := ["bash", "-cu"]

default:
    @just --list

# First-time setup: .env + Python environment + config generation + tests.
install:
    bash ./scripts/bootstrap

# Discover LiteLLM models and interactively map agent profiles into .env.
configure *args:
    python3 ./scripts/configure-models {{args}}

doctor:
    bash ./scripts/doctor

check: config test

config:
    python3 ./scripts/generate-config
    python3 -m json.tool opencode.jsonc >/dev/null
    python3 -m json.tool opencode.v2.jsonc >/dev/null
    @echo "OpenCode V1/V2 configs: generated and valid JSON"

test:
    python3 -m unittest discover -s tests -v

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
    @grep '^MODEL_' .env 2>/dev/null || { echo "Missing .env; run: just install" >&2; exit 1; }

refresh:
    bash ./scripts/bootstrap --refresh

clean:
    rm -rf .venv architecture-inventory.json security-findings.json
