# Changelog

All notable toolkit changes are documented here.

The project uses semantic versioning for tagged releases. `VERSION` is the release source of truth; Git tags use the corresponding `v<version>` form.

## Unreleased

### Changed
- Replace `opencode-mem` with `oc2-memory@0.1.1`, a native OpenCode 2 plugin backed by plain Markdown that can live in an Obsidian vault and/or Git checkout.
- Remove the global `@rehydra/opencode` package configuration during toolkit install when present, and disable `rehydra` plugin IDs in the generated config.

- The toolkit now targets released OpenCode 2 only: `oc` launches the official `opencode` binary and the beta `oc2` / `opencode2` path is removed.
- `just install` removes the legacy `opencode-ai` npm package when present and installs/updates `@opencode/cli@latest`.
- Native configuration is generated only as `opencode.jsonc` using the OpenCode 2 schema.
- `opencode-mem@2.26.0` is the sole runtime plugin configured by the toolkit.
- The obsolete beta usage-pricing plugin and beta-specific CI/tests are removed.
- The Docker runtime now contains one released OpenCode 2 server instead of separate V1/V2 services.

## [0.1.2] - 2026-09-13

Patch release removing semantic delegated-task deduplication.

### Changed

- Fresh delegated tasks are no longer considered identical because they reuse the same description or prompt.
- Each fresh delegation gets its own invocation identity; only an explicit `task_id` means “continue this existing delegated task”.
- `MAX_PARALLEL_SUBAGENTS` and queue timeout remain the concurrency controls, so identical tasks can run concurrently when slots are available without creating phantom `task already running` locks.
- Explicit `task_id` continuations still retain per-task retry accounting and resume semantics.
- The temporary stale-lock recovery wrappers and their child-status heuristics were removed because semantic duplicate locking is no longer part of the active runtime behavior.

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
