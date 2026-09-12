# Changelog

All notable toolkit changes are documented here.

The project uses semantic versioning for tagged releases. `VERSION` is the release source of truth; Git tags use the corresponding `v<version>` form.

## [0.1.1] - 2026-09-13

Patch release for stale delegated-task recovery.

### Fixed

- OpenCode V1/V2 no longer remain permanently blocked by a stale `equivalent delegated task is already running` guard after the delegated child has already become terminal.
- Stale-lock recovery is conservative: it only fails open after a successful child-session lookup proves that no delegated child is active; unknown or active child state keeps the original guard in place.

## [0.1.0] - 2026-09-13

First tagged multi-runtime release.

### Added

- Runtime-neutral canonical agent definitions consumed by OpenCode and Codex adapters.
- Deterministic `oc sync opencode|codex|all` generation with dry-run and drift checking.
- Safe project-local Codex install, doctor and uninstall lifecycle with ownership manifests and conflict protection.
- Portable canonical skills shared across OpenCode and Codex without duplicating skill bodies.
- Portable memory MCP integration exposing read/search/render/propose/candidate operations while keeping accept/promote/push human-controlled.
- OpenCode V1/V2 Docker runtime, isolated sandboxing and dedicated/rootless DinD flows.
- End-to-end runtime acceptance from disposable external projects, including Codex lifecycle regressions and a real authenticated OpenCode V2 HTTP smoke.

### Safety and compatibility

- User-owned or manually modified Codex agents/skills are never silently overwritten or deleted.
- Existing Codex ownership manifest v1 remains readable and migrates safely.
- Runtime acceptance isolates HOME/XDG state and does not read the developer `.env.local`, provider credentials or private memory vault.
- Private memory MCP acceptance uses the real pinned plugin only when dedicated CI access is configured; otherwise it is explicitly skipped rather than simulated.
