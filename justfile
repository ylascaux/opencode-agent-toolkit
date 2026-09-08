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

# Install a reversible per-user command (default: oc) in ~/.local/bin.
install-user command="oc":
    bash ./scripts/user-link install "{{command}}"

# Remove the per-user command only when it points to this toolkit.
uninstall-user command="oc":
    bash ./scripts/user-link uninstall "{{command}}"

# Show whether the per-user command points to this toolkit.
user-status command="oc":
    bash ./scripts/user-link status "{{command}}"

# Optional/future: discover LiteLLM models and create explicit per-agent mappings.
configure *args:
    python3 ./scripts/configure-models {{args}}

configure-litellm *args:
    python3 ./scripts/configure-models {{args}}

doctor:
    bash ./scripts/doctor

# Fast deterministic checks performed before an OpenCode run.
preflight:
    @test -f .env || { echo "Missing .env; run: just install" >&2; exit 1; }; set -a; source .env; [[ -f .env.local ]] && source .env.local; set +a; python3 ./scripts/generate-config >/dev/null; python3 ./scripts/apply-reliability >/dev/null; bash ./scripts/preflight

# Show the effective reliability policy after environment overrides.
reliability:
    @test -f .env || { echo "Missing .env; run: just install" >&2; exit 1; }; set -a; source .env; [[ -f .env.local ]] && source .env.local; set +a; python3 - <<'PY'
    import json, os
    from pathlib import Path
    p=json.loads(Path('reliability.json').read_text())
    print('max_parallel_subagents =', os.getenv('MAX_PARALLEL_SUBAGENTS', p['max_parallel_subagents']))
    print('stalled_timeout_seconds =', os.getenv('SUBAGENT_STALLED_TIMEOUT_SECONDS', p['stalled_timeout_seconds']))
    print('max_agent_duration_seconds =', os.getenv('SUBAGENT_MAX_DURATION_SECONDS', p['max_agent_duration_seconds']))
    print('max_same_error =', os.getenv('MAX_SAME_ERROR', p['max_same_error']))
    print('max_provider_retries =', os.getenv('MAX_PROVIDER_RETRIES', p['max_retries']))
    print('step_caps =')
    for k, v in sorted(p['step_caps'].items()): print(f'  {k}: {v}')
    PY

check: config test

config:
    python3 ./scripts/generate-config
    python3 ./scripts/apply-reliability
    python3 -m json.tool opencode.jsonc >/dev/null
    python3 -m json.tool opencode.v2.jsonc >/dev/null
    @echo "OpenCode V1/V2 configs: generated, reliability-capped and valid JSON"

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
    @test -f .env || { echo "Missing .env; run: just install" >&2; exit 1; }; set -a; source .env; [[ -f .env.local ]] && source .env.local; set +a; python3 ./scripts/resolve-models --show

refresh:
    bash ./scripts/bootstrap --refresh

clean:
    rm -rf .venv architecture-inventory.json security-findings.json
