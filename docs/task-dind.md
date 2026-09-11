# Rootless DinD startup and troubleshooting

Managed tasks and the CI smoke test both invoke `scripts/task-dind`. It starts
`docker:29-dind-rootless` by default (selected in `task-run`) without a host Docker
socket or project bind mount. The workspace and Docker data use named volumes.
The worker-facing API is checked from a sibling container and must report the
`rootless` security option. CI also starts a nested container and verifies a write
to the shared workspace.

Do not add a manual `DOCKERD_ROOTLESS_ROOTLESSKIT_FLAGS=-p ...:2375:2375/tcp`:
[the official image entrypoint](https://github.com/docker-library/docker/blob/master/dockerd-entrypoint.sh)
already configures both the listener and RootlessKit forwarding. Also, the Unix
socket inside RootlessKit's private mount namespace is not a reliable readiness
check from an outer `docker exec`. The helper checks the actual TCP client path.

## Ubuntu 24.04 and later

If RootlessKit reports:

```text
failed to start the child: fork/exec /proc/self/exe: operation not permitted
```

check the host's AppArmor/user namespace policy. Ubuntu's restriction may still
apply with an already-privileged outer container. See the
[Rootless Containers AppArmor guide](https://rootlesscontaine.rs/getting-started/common/apparmor/).

An administrator can explicitly load the supplied **named** profile on the Linux
Docker host and select it for DinD only:

```bash
sudo apparmor_parser -r runtime/apparmor/oat-dind-rootless
export OAT_TASK_DIND_APPARMOR_PROFILE=oat-dind-rootless
oc2 task --repo OWNER/REPO --approved -- "TASK"
```

This profile permits user namespaces for the selected already-privileged daemon;
it is not an additional sandbox. Neither `task-run` nor `task-dind` installs the
profile, changes a sysctl, or disables AppArmor automatically. The CI runner
loads the profile for its smoke test and removes it during cleanup. The global
`kernel.apparmor_restrict_unprivileged_userns` setting is left unchanged.

On Docker Desktop/macOS leave this variable unset; the launcher does not attempt
to install a Linux host profile on macOS. For a remote Docker context, policy must
be installed by an administrator on the daemon host, not the client machine.

After stopping all containers using the profile, it can be unloaded with:

```bash
sudo apparmor_parser -R runtime/apparmor/oat-dind-rootless
```

The readiness window defaults to 120 seconds and can be changed using
`OAT_TASK_DIND_WAIT_SECONDS` (1 to 600). Every Docker API probe has a five-second
timeout. Startup failure prints the probe error and the daemon's last log lines;
it never silently switches to a rootful daemon or the host Docker socket.

## Security boundary

The outer DinD container still needs `--privileged`. This is not VM-grade
isolation. The private per-task network and absence of host mounts limit direct
exposure, but do not prove immunity to container/kernel escapes. The existing
unencrypted Docker API on port 2375 is reachable inside that task network only;
no host port is published. TLS/API authorization is a separate hardening task.
