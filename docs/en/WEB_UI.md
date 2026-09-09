# OpenCode Web UI

The toolkit launcher supports `web` and `serve` directly. There is no separate OpenCode configuration for the Web UI: `oc2 web` uses the same generated V2 config, agents, plugins, models, and permissions as the TUI.

## Quick start

Run from the project OpenCode should work on:

```bash
cd ~/Projects/my-project
oc2 web
```

To use a fixed port:

```bash
oc2 web --port 4096
```

The launcher automatically selects `opencode2` and exports `OPENCODE_CONFIG` to `opencode.v2.jsonc`.

From the toolkit repository, equivalent shortcuts are:

```bash
just web-v2 --port 4096
just serve-v2 --port 4096
```

`just web` and `just serve` use the active OpenCode version configured by the toolkit.

## Authentication

OpenCode protects both `web` and `serve` with HTTP Basic authentication when `OPENCODE_SERVER_PASSWORD` is set. The default username is `opencode`; override it with `OPENCODE_SERVER_USERNAME`.

Export the variables in your shell before starting the server:

```bash
export OPENCODE_SERVER_USERNAME="yoann"
export OPENCODE_SERVER_PASSWORD="change-me"

oc2 web --port 4096
```

The launcher naturally passes these variables to OpenCode. It does not copy them into generated config or write them to the repository.

Do not commit a password to `.env`, `.env.local`, `opencode.v2.jsonc`, or another versioned file. For a persistent secret, prefer a secret manager or system keychain and export the value when the shell starts.

## Local-only access

For Mac-only access:

```bash
oc2 web --hostname 127.0.0.1 --port 4096
```

Then open:

```text
http://127.0.0.1:4096
```

## LAN access

To make the UI reachable from another machine:

```bash
export OPENCODE_SERVER_USERNAME="yoann"
export OPENCODE_SERVER_PASSWORD="change-me"

oc2 web --hostname 0.0.0.0 --port 4096
```

Do not expose an OpenCode server on `0.0.0.0` without a password.

## Web UI and TUI together

Start the Web server first:

```bash
oc2 web --port 4096
```

Then, from another terminal:

```bash
opencode2 attach http://127.0.0.1:4096
```

When authentication is enabled, `attach` reuses `OPENCODE_SERVER_USERNAME` and `OPENCODE_SERVER_PASSWORD` from the environment.

Both clients then share the same server and sessions.

## Headless server

To expose the OpenCode API without opening the Web UI:

```bash
oc2 serve --hostname 127.0.0.1 --port 4096
```

The OpenAPI endpoint is available under `/doc` on the server.

## Verification

After changing the toolkit:

```bash
just test
just web-v2 --help
```

Launcher tests verify that `oc2 web` selects OpenCode V2, uses `opencode.v2.jsonc`, preserves Web arguments, and forwards authentication environment variables without printing the password.
