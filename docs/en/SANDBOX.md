# Agent sandbox and manual cloud diagnostics

The toolkit can execute normal agent shell commands inside a disposable development sandbox while keeping the host filesystem, credentials and cloud identities outside that sandbox.

## Security model

When `OAT_SANDBOX_ENABLED=1`, an OpenCode run creates one persistent Docker/Podman container for the current repository. The container lives only for that OpenCode session so Nix downloads, `direnv` state and build caches remain useful across consecutive agent commands.

```text
OpenCode / agents on host
        |
        | ordinary shell command
        v
OpenCode permission policy
        |
        v
persistent dev sandbox --> repository RW

AWS/Kubernetes evidence needed
        |
        v
agent proposes exact read-only command
        |
        v
user runs it on trusted host
        |
        v
user pastes sanitized output back
```

The sandbox receives:

- the current repository at `/workspace` in read/write mode;
- `.github` over-mounted read-only when it exists;
- Internet access through the selected container runtime bridge;
- a Nix-based bootstrap toolset;
- CPU, memory and PID limits.

It does **not** receive host `~/.aws`, `~/.ssh`, `~/.kube`, Azure/GCloud credentials, GitHub CLI credentials, `SSH_AUTH_SOCK` or the Docker socket.

The runtime starts the container with `--cap-drop=ALL` and `no-new-privileges`. The process is root inside the container because the Nix store must remain writable for project environments, but it has no Linux capabilities and no host credential/socket mounts. On Docker Desktop for macOS the container is additionally behind Docker's Linux VM boundary.

## Nix and direnv

The base image is intentionally lightweight. It contains only bootstrap/repository tools such as Git, Nix, direnv/nix-direnv, Python, curl/wget, jq/yq, ripgrep/fd, just, shellcheck, hadolint and actionlint.

Go, Rust/Cargo, Node.js, PHP/Composer, Helm, OpenTofu, Terragrunt and other project-specific toolchains should come from the target repository's Nix/devenv configuration. This keeps the default image small while still giving each project its exact required versions.

AWS CLI and kubectl are intentionally not part of the base image. A repository may still provide extra tools through Nix, but no host AWS/Kubernetes credentials are mounted and the default OpenCode policy denies direct `aws ...` and `kubectl ...` execution.

Before an ordinary shell command, the runner finds the closest `.envrc`, executes `direnv allow` **inside the sandbox**, exports that environment and then runs the command. A repository-controlled `.envrc` is executable code; sandboxing is what makes automatic allowance acceptable here.

## Enable the sandbox

```bash
just sandbox-on
just sandbox-doctor
```

`just sandbox-on` builds the image and stores `OAT_SANDBOX_ENABLED=1` in `.env.local`. Disable it with:

```bash
just sandbox-off
```

Useful commands:

```bash
just sandbox-build
just sandbox-doctor
just sandbox-clean
```

Existing installations remain opt-in for compatibility. New behavior only activates when `OAT_SANDBOX_ENABLED=1`.

## AWS and Kubernetes debugging

AWS and Kubernetes diagnostics are **manual-only**.

Agents must never execute `aws ...` or `kubectl ...`. Instead, when runtime evidence is needed they provide the smallest useful command, explain what it checks, and ask the user to run it on a trusted host. The user then pastes the sanitized output back into the conversation.

Example:

```text
Agent:
  Please run:
  kubectl get pods -n payments -o wide

  This checks whether the affected workload is scheduled/restarting.
  Paste the output back; no secrets are expected in this command.

User:
  <command output>

Agent:
  analyzes the evidence and, only if necessary, asks for the next minimal command
```

Prefer read-only diagnostics such as:

```bash
aws sts get-caller-identity
aws ec2 describe-instances ...
aws logs tail ...

kubectl get ...
kubectl describe ...
kubectl logs ...
kubectl events ...
kubectl auth can-i ...
```

Do **not** ask the user to return secrets, tokens, kubeconfigs, passwords or private keys. Avoid commands such as `aws secretsmanager get-secret-value`, decrypted SSM reads, authorization-token retrieval, or `kubectl get secrets -o yaml/json`. If a diagnostic output may contain sensitive values, request a filtered/redacted form.

This manual evidence loop has two useful properties: cloud credentials never enter the agent runtime, and the user sees every real infrastructure command before it runs.

## Network boundary

The default sandbox network mode is `bridge` because Nix, package managers and source tooling need Internet access. Docker/Podman bridge networking is **not** a strict egress or LAN allowlist. Do not assume it prevents access to private network ranges.

For higher-assurance environments, place the sandbox behind an egress proxy/firewall and allow only required package registries and public services. `sandbox/policy.json` calls this limitation out explicitly so it cannot be mistaken for a stronger network guarantee.

## Docker builds

The host Docker socket is never mounted. The standard sandbox can lint and inspect Dockerfiles but cannot control the host Docker daemon. If real image builds are required, add a separate rootless BuildKit/build profile rather than exposing `/var/run/docker.sock`.

## Trust boundaries

The intended boundaries are:

1. agent prompt and generated capability map;
2. OpenCode `allow / ask / deny` permissions;
3. sandbox command routing;
4. container filesystem/resource isolation;
5. no host credential/socket mounts;
6. manual user-mediated AWS/Kubernetes diagnostics.

A failure in one layer should therefore not automatically grant host filesystem or cloud access.
