# OpenCode Web UI

The toolkit keeps a convenient `oc2 web` command, but OpenCode 2 beta currently has **no native `web` subcommand**. In the V2 CLI, `web` would otherwise be interpreted as a project directory. The launcher therefore translates:

```text
oc2 web ...
        ↓
opencode2 serve ...
```

The V2 server exposes the HTTP API and serves the browser UI. It uses the same generated V2 config, agents, plugins, models, permissions, and guardrails as the TUI.

## Quick start

Run from the project OpenCode should work on:

```bash
cd ~/Projects/my-project
oc2 web --port 4096
```

The launcher selects `opencode2`, exports `OPENCODE_CONFIG` to `opencode.v2.jsonc`, and maps `web` to `serve`.

You can also call the native V2 command directly:

```bash
oc2 serve --hostname 127.0.0.1 --port 4096
```

From the toolkit repository:

```bash
just web-v2 --port 4096
just serve-v2 --port 4096
```

`just web` uses the active OpenCode version. On V1 it calls the real `opencode web`; on V2 the launcher applies the `web -> serve` compatibility alias.

## Open the UI

Unlike V1 `opencode web`, `opencode2 serve` is not a dedicated `web` command. With a fixed port:

```bash
oc2 web --hostname 127.0.0.1 --port 4096
```

then open:

```text
http://127.0.0.1:4096
```

## Authentication

Authentication environment variables are inherited by the launcher and are never copied into generated config:

```bash
export OPENCODE_SERVER_USERNAME="yoann"
export OPENCODE_SERVER_PASSWORD="change-me"

oc2 web --hostname 127.0.0.1 --port 4096
```

Do not commit the password to `.env`, `.env.local`, `opencode.v2.jsonc`, or another versioned file. For a persistent secret, prefer a system keychain or secret manager and export it when starting the shell.

OpenCode 2 is still beta and its server-authentication behavior is evolving. If a beta build rejects known-good credentials, check the installed beta version and current V2 issues before changing the toolkit.

## Local-only access

Recommended Mac-only setup:

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

Do not expose the server on `0.0.0.0` unless authentication is working.

## Web UI and TUI together

Start the server:

```bash
oc2 web --port 4096
```

Open the browser at:

```text
http://127.0.0.1:4096
```

To connect the V2 TUI to the same server, use the V2 `--server` option:

```bash
opencode2 --server http://127.0.0.1:4096
```

This replaces the older V1 `attach` workflow, which is not a current V2 subcommand.

## API

The native V2 command is:

```bash
oc2 serve --hostname 127.0.0.1 --port 4096
```

It exposes the V2 HTTP server used by OpenCode clients. The toolkit keeps `oc2 web` as an ergonomic compatibility alias so `web` is not misinterpreted as a directory.

## Verification

After changing the toolkit:

```bash
just test
just web-v2 --port 4096
```

Launcher tests verify that `oc2 web` selects OpenCode V2, uses `opencode.v2.jsonc`, translates `web` to `serve`, preserves arguments, and forwards authentication environment variables without printing the password.
