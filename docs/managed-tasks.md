# Managed tasks: clone -> agents -> PR

Managed tasks are the high-isolation delivery path for OpenCode V2. They are designed for work that should start from a Git repository rather than from a host filesystem bind.

## Command

```bash
export OAT_GITHUB_TOKEN='...'
oc2 task --repo owner/repository --approved -- "implement the requested change"
```

The GitHub credential should be scoped to the repositories the toolkit is allowed to modify. A fine-grained token typically needs repository Contents read/write and Pull requests read/write. Branch protection/rulesets remain the protection for `main`; Git cannot express a useful permission such as “may edit files but may never delete a file”.

The token is consumed only by trusted broker containers. It is not injected into OpenCode or its leaf agents.

## Lifecycle

1. `task-run` creates a unique Docker network and ephemeral named volumes.
2. A trusted `workspace-broker` clones `--base` into `/workspace` and creates a generated `agent/<timestamp>-<slug>` branch.
3. Toolkit memory/plugin data are copied into a per-run snapshot volume. The durable memory directory is not mounted into the worker.
4. A dedicated `docker:29-dind-rootless` daemon starts for this task. It has no host Docker socket and no host project bind.
5. OpenCode V2 starts in standalone mode with the `orchestrator` agent and the `[MANAGED_TASK_ROOT_APPROVED]` contract.
6. The orchestrator delegates implementation/testing/review/security work using the normal two-level agent hierarchy.
7. On worker failure, no Git branch is pushed and no PR is created.
8. On worker success, a trusted memory broker imports only validated quarantine candidate JSON files.
9. A trusted workspace broker stages the workspace, creates the commit, pushes exactly `HEAD:refs/heads/agent/...`, and creates a PR against `--base`.
10. The launcher reports success only after GitHub returned a PR number and URL.
11. Ephemeral network/workspace/DinD/task-memory volumes are removed. The OpenCode managed-task home remains persistent for provider authentication.

Use `--keep` while debugging to preserve the per-run resources.

## Trust boundaries

### OpenCode worker

The worker receives:

- the ephemeral `/workspace` volume;
- a disposable toolkit-memory snapshot;
- a disposable candidate/reliability state volume;
- a persistent OpenCode home containing provider authentication/session state;
- network access;
- `DOCKER_HOST=tcp://docker-agent:2375` targeting only the task DinD daemon.

It does **not** receive:

- `OAT_GITHUB_TOKEN` / `GITHUB_TOKEN`;
- `/var/run/docker.sock` from the host;
- the user's local project checkout;
- `~/.ssh`;
- AWS config/credentials;
- kubeconfig;
- the durable memory/state directories.

The OpenCode provider credential remains in its OpenCode home because the process needs it to call the model. This design does not attempt to isolate the model credential from OpenCode itself.

### Workspace broker

The broker is short-lived and receives only:

- GitHub token;
- workspace volume;
- repository/base/generated-branch metadata.

It validates repository/ref syntax, only permits generated branches under `agent/`, refuses `main`/`master` as the destination branch, stores no token in the Git remote URL, and pushes only the workspace `HEAD` to the generated branch.

The broker never merges a PR.

### Memory broker

The worker may only mutate its task-local state. After a successful run the memory broker reads `memory/candidates/*.json` and validates regular-file status, maximum size, filename/fingerprint consistency, candidate id, kind, confidence and bounded text fields. Only valid candidate files are copied/merged into durable **candidate quarantine**.

A managed task cannot directly accept or promote its own memory candidate.

## Why PR creation is outside the agent

The agent can decide what code should change, but publication is a deterministic control-plane action. Keeping credentials outside the worker gives the final state machine a useful invariant:

```text
TASK_SUCCESS = worker_success && commit_created && branch_pushed && pull_request_created
```

A model saying “done” is therefore not sufficient for the launcher to report success.

## Plan approval

Normal OpenCode V2 work keeps `PLAN_APPROVAL_MODE=changes` by default. Managed tasks are non-interactive and require an explicit `--approved` flag. Only that worker receives `PLAN_APPROVAL_MODE=off`, together with the root-approved managed-task marker. Normal `oc2` sessions are unchanged.

`--approved` approves the requested scope, not arbitrary later expansion. The orchestrator contract still requires it to stop rather than materially broaden scope.

## Failure behavior

Before publication, a failed worker leaves GitHub untouched. By default ephemeral resources are cleaned up; pass `--keep` to inspect them.

A failure during push/PR creation causes the overall command to fail. The generated branch can exist if push succeeded before PR creation failed; the launcher must not claim success without the PR URL.

No automatic merge is performed.
