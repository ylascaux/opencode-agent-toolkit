set shell := ["bash", "-euo", "pipefail", "-c"]
set positional-arguments

default:
    @just --list

# Install/update OpenCode 2 stable, configure the memory plugin, and install oc.
install:
    bash ./scripts/bootstrap

# Remove toolkit-owned launcher links. Keep OpenCode, auth, plugins and profiles.
uninstall:
    bash ./scripts/user-link uninstall oc
    bash ./scripts/user-link uninstall oc2 || true

# Apply a model profile; .env.local overrides are preserved.
profile name="copilot":
    python3 ./scripts/apply-profile "$1"

# Regenerate the stable OpenCode configuration.
config:
    python3 -B ./scripts/configure-local

# Check OpenCode 2, config drift and installed plugins.
doctor:
    bash ./scripts/doctor

# Contributor tests.
test:
    python3 -m unittest discover -s tests -v
    node --test tests/*.test.mjs

# Stable OpenCode 2. Prefer the installed oc command from the target project.
oc *args:
    bash ./scripts/opencode-agents "$@"

# Inspect plugins using OpenCode's native plugin manager.
plugins:
    opencode plugin list

# Synchronize generated artifacts, including Codex.
sync *args:
    python3 -B ./scripts/sync-runtime "$@"

# Codex project installation/update/doctor/uninstall.
codex *args:
    python3 -B ./scripts/codex "$@"

[private]
check: config test
