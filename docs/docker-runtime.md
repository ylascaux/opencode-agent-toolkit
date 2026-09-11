# Docker runtime for `oc` and `oc2`

The toolkit uses Docker as its default OpenCode runtime. The host only needs Docker, Git/Bash and optionally `just`; Node.js, Python dependencies, OpenCode V1/V2, Nix and plugin dependencies live in the runtime image.

## Architecture

Two persistent services share one runtime image but keep separate OpenCode home volumes:

- `oc-server`: OpenCode V1, host URL `http://127.0.0.1:4095`
- `oc2-server`: OpenCode V2 beta, host URL `http://127.0.0.1:4096`
- `oc-home`: V1 auth, sessions, cache and local state
- `oc2-home`: V2 auth, sessions, cache and local state

Only toolkit-owned persistent data and state are shared between the two services and the host. By default those are `~/.local/share/opencode-agent-toolkit` and `~/.local/state/opencode-agent-toolkit`, containing memory/plugin data, candidates, reliability checkpoints and related toolkit state. The rest of the host home, including `~/.ssh`, is not mounted.

Normal interactive sessions bind-mount the selected host workspace, but OpenCode no longer receives the host Docker socket. Docker commands target the dedicated `docker-agent` DinD service over the private Compose network.

OpenCode V2 OpenAI/ChatGPT OAuth redirects the browser to `http://localhost:1455/auth/callback`. The Docker runtime therefore publishes container port `1455` on host loopback only (`127.0.0.1:${OAT_OC2_OAUTH_PORT:-1455}`), so browser authentication works without exposing the callback to the LAN.

## Installation

```bash
just install
just install-user
just install-oc2
```

`just install` builds `opencode-agent-toolkit:local`. It does not create a host Python virtualenv or install npm/OpenCode packages on the host when `OAT_RUNTIME=docker`.

Use `just refresh` to rebuild the runtime image without the Docker build cache.

On first use, if `~/.local/share/opencode/auth.json` already exists, the wrapper copies it once into the selected private runtime home (`oc-home` or `oc2-home`) and restarts that server. This preserves an existing OpenCode login without exposing the whole host data directory. Disable this with `OAT_IMPORT_HOST_AUTH=0`.

## Daily usage

From a repository:

```bash
oc
oc run "review this repository"

oc2
oc2 run "fix the failing tests"
```

The wrapper starts the corresponding server automatically and then connects a client inside the same container. The current Git repository root is the default workspace boundary. Outside a Git repository, the current directory is used.

Server controls are available through either launcher:

```bash
oc server status
oc server logs
oc server restart
oc server stop

oc2 server status
oc2 server logs
oc2 server restart
oc2 server stop
```

Do not run `docker compose up ...` directly unless you also provide the runtime-generated `OAT_WORKSPACE_ROOT`, `OAT_DATA_DIR`, and `OAT_STATE_DIR` variables. The `oc`/`oc2` wrappers calculate and export those values before invoking Compose.

Open an interactive shell in the runtime with:

```bash
oc2 shell
```

Toolkit memory commands also execute inside the runtime while using the shared toolkit data/state directories:

```bash
oc2 memory status
oc2 memory sync
```

## Connecting with a native client

The servers are published on loopback, so a native client can connect if one happens to be installed on the host:

```bash
opencode attach http://127.0.0.1:4095 --dir "$PWD"
opencode2 --server http://127.0.0.1:4096
```

A host installation is optional; the `oc` and `oc2` wrappers already run their clients from inside the image.

The native client must reference a path visible to the running server. If you regularly switch repositories while keeping the same server alive, set a broader `OAT_WORKSPACE_ROOT` such as `$HOME/Projects`.

## Workspace scope

By default only the current Git repository is exposed read/write. Switching to a repository outside the current bind causes Compose to recreate the service with the new workspace mount, while the OpenCode home volume keeps its persistent state.

To deliberately grant a broader tree and avoid recreating the server when moving between repositories, set an absolute path in `.env.local`:

```bash
OAT_WORKSPACE_ROOT=$HOME/Projects
```

Then any invocation whose current directory is under that path can use the same persistent server. This is useful for multi-repository architecture work.

## Memory and private plugin repositories

The toolkit data bind mount reuses an existing local memory vault and `opencode-memory-plugin` checkout. This is particularly useful because the default memory plugin repository is private and uses an SSH Git URL.

The container does **not** receive `~/.ssh` or the host SSH agent. If an existing private checkout cannot be updated, the memory plugin's non-strict mode keeps using the local snapshot. A completely fresh private clone still needs an explicit authentication method; do not solve that by mounting the whole SSH directory into the runtime.

## Docker access and security

OpenCode containers no longer receive `/var/run/docker.sock`. Normal interactive sessions use a dedicated DinD daemon, and managed tasks use an even narrower per-run rootless DinD daemon with an ephemeral workspace volume.

Keep OpenCode server ports and the OAuth callback bound to `127.0.0.1`. The V1 and V2 homes are intentionally separate so beta V2 state cannot corrupt V1 state.

## Configuration

Useful settings:

```bash
OAT_RUNTIME=docker
OAT_RUNTIME_IMAGE=opencode-agent-toolkit:local
OAT_OC_PORT=4095
OAT_OC2_PORT=4096
OAT_OC2_OAUTH_PORT=1455
OAT_IMPORT_HOST_AUTH=1
# OAT_OPENCODE_V1_VERSION=latest
# OAT_OPENCODE_V2_VERSION=beta
# OAT_WORKSPACE_ROOT=$HOME/Projects
# OAT_DATA_DIR=$HOME/.local/share/opencode-agent-toolkit
# OAT_STATE_DIR=$HOME/.local/state/opencode-agent-toolkit
# OAT_HOST_AUTH_FILE=$HOME/.local/share/opencode/auth.json
```

Set `OAT_RUNTIME=host` only to temporarily use the legacy host launcher.
