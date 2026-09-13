set shell := ["bash", "-eu", "-o", "pipefail", "-c"]
set positional-arguments

default:
    @just --list

# Install both native launchers; preserve existing model and memory settings.
install:
    bash ./scripts/bootstrap

# Apply a model-provider profile; keep per-agent overrides in .env.local.
profile name="copilot":
    python3 ./scripts/apply-profile "$1"

# Generate the native configurations (optional memory included).
config:
    bash ./scripts/opencode-agents config

# Local diagnostics; no provider calls or background service.
doctor:
    bash ./scripts/doctor

# Launch native OpenCode V1 in the directory where just was invoked.
oc *args:
    cd "{{invocation_directory()}}" && OPENCODE_MAJOR=1 bash "{{justfile_directory()}}/scripts/opencode-agents" "$@"

# Launch native OpenCode V2 in the directory where just was invoked.
oc2 *args:
    cd "{{invocation_directory()}}" && OPENCODE_MAJOR=2 bash "{{justfile_directory()}}/scripts/opencode-agents" "$@"

# Sync canonical agents/skills to a runtime, including Codex.
sync *args:
    cd "{{invocation_directory()}}" && bash "{{justfile_directory()}}/scripts/opencode-agents" sync "$@"

# Codex installation/update/status without OpenCode or a toolkit .env.
codex *args:
    cd "{{invocation_directory()}}" && bash "{{justfile_directory()}}/scripts/opencode-agents" codex "$@"

# One memory command: enable, disable, status, sync, candidates, accept, ...
memory *args:
    cd "{{invocation_directory()}}" && bash "{{justfile_directory()}}/scripts/opencode-agents" memory "$@"

# Contributor tests; not run implicitly during installation or startup.
test:
    python3 -m unittest discover -s tests -v
    node --test tests/*.test.mjs

# Complete contributor validation.
check: config test
