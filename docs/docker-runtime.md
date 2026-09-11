# Docker runtime for `oc` and `oc2`

The toolkit uses Docker as its default OpenCode runtime. The host only needs Docker, Git/Bash and optionally `just`; Node.js, Python dependencies, OpenCode V1/V2, Nix and plugin dependencies live in the runtime image.

## Architecture

Two persistent services share one runtime image but keep separate OpenCode home volumes:

- `oc-server`: OpenCode V1, host URL `http://127.0.0.1:4095`
- `oc2-server`: OpenCode V2 beta, host URL `http://127.0.0.1:4096`
- `oc-home`: V1 auth, sessions, cache and local state
- `oc2-home`: V2 auth, sessions, cache and local state

Only toolkit-owned persistent data is shared between the two services and the host. By default that is `~/.local/share/opencode-agent-toolkit`, containing memory/plugin state and related toolkit data. The rest of the host home, including `~/.ssh`, is not mounted.

The active workspace is bind-mounted at the **same absolute path** inside the runtime container as on the host. This is intentional: the Docker CLI inside the container talks to the host Docker daemon. Keeping identical paths means `docker build`, `docker run -v`, and `docker compose` can pass bind-mount paths that the host daemon understands.

The host Docker socket is mounted at `/var/run/docker.sock`. This is Docker-outside-of-Docker, not Docker-in-Docker; containers created by an agent are normal host Docker containers.

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

Open an interactive shell in the runtime with:

```bash
oc2 shell
```

Toolkit memory commands also execute inside the runtime while using the shared toolkit data directory:

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

Mounting the host Docker socket is effectively host-level privilege. An agent that can issue unrestricted Docker commands can create a container that mounts host files regardless of the normal workspace bind mount.

For that reason:

- keep OpenCode server ports bound to `127.0.0.1`;
- keep the toolkit permission/approval rules around destructive Docker commands;
- do not treat the runtime container itself as a security boundary once the Docker socket is mounted;
- use the existing inner sandbox when a task needs a stronger command boundary and does not require unrestricted host Docker access.

The V1 and V2 homes are intentionally separate so beta V2 state cannot corrupt V1 state.

## Configuration

Useful settings:

```bash
OAT_RUNTIME=docker
OAT_RUNTIME_IMAGE=opencode-agent-toolkit:local
OAT_OC_PORT=4095
OAT_OC2_PORT=4096
OAT_IMPORT_HOST_AUTH=1
# OAT_OPENCODE_V1_VERSION=latest
# OAT_OPENCODE_V2_VERSION=beta
# OAT_DOCKER_SOCKET=$HOME/.docker/run/docker.sock
# OAT_WORKSPACE_ROOT=$HOME/Projects
# OAT_DATA_DIR=$HOME/.local/share/opencode-agent-toolkit
# OAT_HOST_AUTH_FILE=$HOME/.local/share/opencode/auth.json
```

Set `OAT_RUNTIME=host` only to temporarily use the legacy host launcher.
