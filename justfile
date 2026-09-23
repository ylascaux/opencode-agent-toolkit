set shell := ["bash", "-euo", "pipefail", "-c"]
set positional-arguments

default:
    @just --list

# Install/update OpenCode 2 stable, generate config and install ~/.local/bin/oc.
install:
    bash ./scripts/bootstrap

# Remove only the toolkit-owned launcher. Keep OpenCode, auth and memory data.
uninstall:
    bash ./scripts/user-link uninstall oc
    bash ./scripts/user-link uninstall oc2 || true

# Apply a model profile; .env.local overrides are preserved.
profile name="copilot":
    python3 ./scripts/apply-profile "$1"

# Regenerate the OpenCode 2 native configuration.
config:
    python3 -B ./scripts/configure-local

# Check local binary and config drift without contacting model providers.
doctor:
    bash ./scripts/doctor

# Contributor tests.
test:
    python3 -m unittest discover -s tests -v
    node --test tests/*.test.mjs

# OpenCode 2 stable. Prefer the installed oc command from the target project.
oc *args:
    bash ./scripts/opencode-agents "$@"

# Synchronize runtime artifacts, including Codex; supports --dry-run and --check.
sync *args:
    python3 -B ./scripts/sync-runtime "$@"

# Codex project installation/update/doctor/uninstall (no OpenCode required).
codex *args:
    python3 -B ./scripts/codex "$@"

# Legacy private memory CLI kept only for Codex/MCP compatibility.
memory *args:
    bash ./scripts/opencode-agents memory "$@"

[private]
check: config test
