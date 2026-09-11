# Docker runtime for `oc` and `oc2`

The toolkit uses Docker as its default OpenCode runtime. The host needs Docker, Git/Bash and optionally `just`; Node.js, Python dependencies, OpenCode V1/V2, Nix and plugin dependencies live in the runtime image.

## Normal interactive architecture

Two persistent OpenCode services share one runtime image but keep separate home volumes:

- `oc-server`: OpenCode V1, host URL `http://127.0.0.1:4095`
- `oc2-server`: OpenCode V2 beta, host URL `http://127.0.0.1:4096`
- `oc-home`: V1 auth, sessions, cache and local state
- `oc2-home`: V2 auth, sessions, cache and local state
- `docker-agent`: dedicated Docker-in-Docker daemon used by both OpenCode services

The host Docker socket is **not** mounted in `oc-server` or `oc2-server`. Docker commands issued by OpenCode target `tcp://docker-agent:2375` on the private Compose network. The DinD API is not published to the host.

Normal interactive use still bind-mounts the active host repository into both OpenCode and `docker-agent` at the same absolute path. That preserves the familiar workflow where edits immediately appear in the user's checkout and lets nested `docker compose` bind mounts resolve inside DinD. It also means normal interactive mode is not a strict filesystem sandbox: the selected workspace is intentionally exposed read/write.

Only toolkit-owned persistent data/state are shared with normal OpenCode sessions. By default these are `~/.local/share/opencode-agent-toolkit` and `~/.local/state/opencode-agent-toolkit`. The rest of the host home, including `~/.ssh`, AWS config and kubeconfig, is not mounted.

## Managed task architecture

For a stronger boundary use `oc2 task`. Managed tasks do **not** bind-mount the host project at all:

```text
Git broker (GitHub credential)
        |
        | clone
        v
 ephemeral workspace volume
        |
        +--> OpenCode V2 orchestrator/leaf agents
        |
        +--> dedicated rootless DinD
        |
        +--> Git broker -> push agent/... -> PR
```

Each run gets a fresh workspace volume, fresh task state and a fresh rootless DinD data volume. The GitHub token exists only in the short-lived trusted Git broker containers used for clone and publication; it is never passed to the OpenCode worker. The worker receives neither the host Docker socket nor a host project bind.

See [`managed-tasks.md`](managed-tasks.md) for the full lifecycle and threat-boundary details.

## Installation

```bash
just install
just install-user
just install-oc2
```

`just install` builds `opencode-agent-toolkit:local`. It does not create a host Python virtualenv or install npm/OpenCode packages on the host when `OAT_RUNTIME=docker`.

Use `just refresh` to rebuild the runtime image without the Docker build cache.

On first use, if `~/.local/share/opencode/auth.json` already exists, the wrapper copies it once into the selected private runtime home and, for managed tasks, into the persistent managed-task OpenCode home. Disable this with `OAT_IMPORT_HOST_AUTH=0`.

## Daily interactive usage

```bash
oc
oc run "review this repository"

oc2
oc2 run "fix the failing tests"
```

Server controls remain unchanged:

```bash
oc2 server status
oc2 server logs
oc2 server restart
oc2 server stop
```

`server status` also reports the dedicated DinD service.

Open a shell in the normal persistent runtime with:

```bash
oc2 shell
```

Memory commands continue to work normally:

```bash
oc2 memory status
oc2 memory sync
```

## Managed task usage

A managed run is intentionally explicit and V2-only:

```bash
export OAT_GITHUB_TOKEN='...'
oc2 task --repo owner/repository --approved -- "fix the failing tests"
```

Optional controls:

```bash
oc2 task \
  --repo owner/repository \
  --base main \
  --title "fix: repair failing tests" \
  --approved \
  -- "fix the failing tests"
```

`--approved` is required because this path is non-interactive. It represents explicit root approval for the requested execution scope and disables the normal plan pause **only inside that managed run**. Material scope broadening remains forbidden by the orchestrator contract.

The run is not considered complete merely because files changed. Success requires the worker to exit successfully and the trusted broker to commit, push the generated `agent/...` branch and create a pull request. If publication fails, the command fails.

## Workspace scope for normal sessions

By default only the current Git repository is exposed read/write. Switching to a repository outside the current bind causes Compose to recreate the affected services while persistent home/DinD volumes retain state.

To deliberately grant a broader tree to normal interactive sessions, set an absolute path in `.env.local`:

```bash
OAT_WORKSPACE_ROOT=$HOME/Projects
```

`oc2 task` ignores `OAT_WORKSPACE_ROOT`; managed projects are always cloned into an ephemeral Docker volume.

## Memory

Normal sessions continue to use the toolkit's durable memory/plugin directories directly.

Managed tasks use a different boundary:

1. toolkit-owned memory/plugin data are copied read-only-from-host into a per-run Docker volume;
2. the OpenCode worker operates on that disposable snapshot;
3. candidate capture, when enabled, writes only to the per-run state volume;
4. after a successful run, `memory-broker` validates candidate filename/fingerprint, JSON shape, kind, confidence and size;
5. only validated `candidates/*.json` files are merged into the durable quarantine state;
6. accepted/promoted memory is never mutated automatically by a managed worker.

This preserves project/hats/workstyle context without granting the agent direct write access to durable memory.

## Docker security model

Normal interactive mode uses a dedicated **rootful** DinD service for compatibility with host bind-mounted source trees. The DinD container is privileged, so it must not be treated as a perfect hostile-code sandbox. The important improvement over Docker-outside-of-Docker is that OpenCode no longer receives the host daemon socket; Docker operations are scoped to the dedicated daemon and the explicitly mounted workspace.

Managed tasks use a fresh `docker:29-dind-rootless` daemon. Docker's rootless DinD image still needs a privileged outer container for RootlessKit, but the daemon itself runs as an unprivileged user and receives only ephemeral named volumes. It has no host project bind and no host Docker socket.

Neither mode injects `~/.ssh`, AWS credentials or kubeconfig by default. Model-provider credentials stored in the OpenCode home remain available to the OpenCode process because they are required to use the provider; do not treat the OpenCode process itself as hostile credential isolation.

## Configuration

Useful settings:

```bash
OAT_RUNTIME=docker
OAT_RUNTIME_IMAGE=opencode-agent-toolkit:local
OAT_DIND_IMAGE=docker:29-dind
OAT_TASK_DIND_IMAGE=docker:29-dind-rootless
OAT_TASK_HOME_VOLUME=opencode-agent-toolkit-task-home-v2
OAT_OC_PORT=4095
OAT_OC2_PORT=4096
OAT_IMPORT_HOST_AUTH=1
# OAT_WORKSPACE_ROOT=$HOME/Projects
# OAT_DATA_DIR=$HOME/.local/share/opencode-agent-toolkit
# OAT_STATE_DIR=$HOME/.local/state/opencode-agent-toolkit
# OAT_HOST_AUTH_FILE=$HOME/.local/share/opencode/auth.json
```

Set `OAT_RUNTIME=host` only to temporarily use the legacy host launcher. Managed tasks require the Docker runtime.
