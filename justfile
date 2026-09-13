set shell := ["bash", "-euo", "pipefail", "-c"]
set positional-arguments

default:
    @just --list

# Generate native configs and install oc/oc2 in ~/.local/bin. No Docker or package installation.
install:
    bash ./scripts/bootstrap

# Remove only toolkit-owned launcher symlinks. Keep profiles, auth and memory.
uninstall:
    bash ./scripts/user-link uninstall oc
    bash ./scripts/user-link uninstall oc2

# Apply a model profile; .env.local overrides are preserved.
profile name="copilot":
    python3 ./scripts/apply-profile "$1"

# Regenerate both native configurations; no network or provider calls.
config:
    python3 -B ./scripts/configure-local

# Check local binaries and config drift without contacting providers.
doctor:
    bash ./scripts/doctor

# Contributor tests (Python development dependencies and Node required).
test:
    python3 -m unittest discover -s tests -v
    node --test tests/*.test.mjs

# Native OpenCode V1. Prefer the installed oc command from the target project.
oc *args:
    OPENCODE_MAJOR=1 bash ./scripts/opencode-agents "$@"

# Native OpenCode V2. Prefer the installed oc2 command from the target project.
oc2 *args:
    OPENCODE_MAJOR=2 bash ./scripts/opencode-agents "$@"

# Synchronize runtime artifacts, including Codex; supports --dry-run and --check.
sync *args:
    python3 -B ./scripts/sync-runtime "$@"

# Codex project installation/update/doctor/uninstall (no OpenCode required).
codex *args:
    python3 -B ./scripts/codex "$@"

# Memory CLI; use `oc memory ...` inside a project for correct project context.
memory *args:
    bash ./scripts/opencode-agents memory "$@"

# Compatibility for existing CI/contributor scripts; hidden from the daily menu.
[private]
check: config test
