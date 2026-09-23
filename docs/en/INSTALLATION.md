# Installation

The toolkit targets **stable OpenCode 2 only**. The user-facing command is
`oc`, which launches the official `opencode` binary.

## macOS quick start

Prerequisites: Bash, Python 3.11+, `just`, and npm.

```bash
brew install just
git clone https://github.com/ylascaux/opencode-agent-toolkit.git
cd opencode-agent-toolkit
just install
just doctor
```

`just install` updates OpenCode through `@opencode/cli@latest`, removes the
legacy `opencode-ai` package, generates the stable config, and installs
`opencode-mem@2.26.0` through `opencode plugin add`.

It installs only this toolkit launcher:

```text
~/.local/bin/oc -> <toolkit>/scripts/opencode-agents
```

Any obsolete toolkit-managed `oc2` link is removed automatically.

## Manage OpenCode separately

If OpenCode is installed through Homebrew or another mechanism:

```bash
OAT_INSTALL_OPENCODE=0 just install
```

To skip plugin installation/update:

```bash
OAT_INSTALL_PLUGINS=0 just install
```

## Default model profile

```text
LOW    -> github-copilot/gpt-5.6-luna
MEDIUM -> github-copilot/gpt-5.6-terra
HIGH   -> github-copilot/gpt-5.6-sol
```

Switch profiles with:

```bash
just profile copilot
just profile codex
```

Persistent per-agent overrides belong in `.env.local`.

## Run from anywhere

```bash
cd ~/Projects/my-api
oc
oc run "Run the tests"
oc plugin list
```

The current directory remains the OpenCode workspace.

## Diagnostics

```bash
just doctor
opencode --version
opencode plugin list
opencode plugin check
```

`just uninstall` removes only toolkit-managed launcher links. It does not
remove OpenCode, authentication state, or plugins.
