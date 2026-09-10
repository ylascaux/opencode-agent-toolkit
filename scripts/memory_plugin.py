#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


TRUTHY = {"1", "true", "yes", "on"}
ROOT = Path(__file__).resolve().parents[1]
PLUGIN_CONFIG_PATH = ROOT / "config" / "plugins.json"
MEMORY_PLUGIN_NAME = "opencode-memory-plugin"


def _load_memory_plugin_config(path: Path = PLUGIN_CONFIG_PATH) -> tuple[str, str]:
    try:
        payload = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise SystemExit(f"External plugin config not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid external plugin config {path}: {exc}") from exc

    try:
        config = payload["plugins"][MEMORY_PLUGIN_NAME]
        repo = config["repository"].strip()
        ref = config["ref"].strip()
    except (KeyError, AttributeError, TypeError) as exc:
        raise SystemExit(
            f"External plugin config {path} must define plugins.{MEMORY_PLUGIN_NAME}.repository and .ref"
        ) from exc

    if not repo or not ref:
        raise SystemExit(
            f"External plugin config {path} must define non-empty repository and ref for {MEMORY_PLUGIN_NAME}"
        )
    return repo, ref


@dataclass(frozen=True)
class PluginSettings:
    repo: str
    ref: str
    directory: Path
    auto_sync: bool
    sync_interval_seconds: int
    strict: bool

    @classmethod
    def from_env(cls) -> "PluginSettings":
        configured_repo, configured_ref = _load_memory_plugin_config()
        data_home = Path(os.getenv("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
        repo = os.getenv("OAT_MEMORY_PLUGIN_REPO", configured_repo).strip()
        ref = os.getenv("OAT_MEMORY_PLUGIN_REF", configured_ref).strip()
        if not repo:
            raise SystemExit("OAT_MEMORY_PLUGIN_REPO override cannot be empty")
        if not ref:
            raise SystemExit("OAT_MEMORY_PLUGIN_REF override cannot be empty")
        return cls(
            repo=repo,
            ref=ref,
            directory=Path(
                os.getenv(
                    "OAT_MEMORY_PLUGIN_DIR",
                    str(data_home / "opencode-agent-toolkit" / "plugins" / MEMORY_PLUGIN_NAME),
                )
            ).expanduser(),
            auto_sync=os.getenv("OAT_MEMORY_PLUGIN_AUTO_SYNC", "1").strip().lower() in TRUTHY,
            sync_interval_seconds=max(0, int(os.getenv("OAT_MEMORY_PLUGIN_SYNC_INTERVAL_SECONDS", "300"))),
            strict=os.getenv("OAT_MEMORY_STRICT", "0").strip().lower() in TRUTHY,
        )


def _git(args: list[str], *, cwd: Path | None = None, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def _run(args: list[str], *, cwd: Path, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        env=os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def _stamp(directory: Path) -> Path:
    return directory / ".git" / "oat-plugin-last-sync"


def _sync_due(settings: PluginSettings, *, force: bool) -> bool:
    if force:
        return True
    if not settings.auto_sync:
        return False
    stamp = _stamp(settings.directory)
    if not stamp.exists():
        return True
    return (time.time() - stamp.stat().st_mtime) >= settings.sync_interval_seconds


def _fail(settings: PluginSettings, message: str) -> None:
    if settings.strict:
        raise SystemExit(message)
    print(f"OpenCode memory plugin: {message}", file=os.sys.stderr)


def _checkout_ref(settings: PluginSettings, *, force_sync: bool) -> None:
    directory = settings.directory
    if not (directory / ".git").is_dir() or not _sync_due(settings, force=force_sync):
        return
    fetch = _git(["fetch", "--quiet", "origin", "--tags"], cwd=directory)
    if fetch.returncode != 0:
        _fail(settings, fetch.stderr.strip() or "git fetch failed; using local plugin snapshot")
        return
    ref = settings.ref
    if ref in {"main", "master"}:
        checkout = _git(["checkout", "--quiet", ref], cwd=directory)
        pull = _git(["pull", "--ff-only", "--quiet", "origin", ref], cwd=directory) if checkout.returncode == 0 else checkout
        result = pull
    else:
        result = _git(["checkout", "--quiet", "--detach", ref], cwd=directory)
    if result.returncode != 0:
        _fail(settings, result.stderr.strip() or f"cannot checkout plugin ref {ref}; using local snapshot")
        return
    _stamp(directory).touch()


def ensure_plugin(*, force_sync: bool = False, settings: PluginSettings | None = None) -> Path:
    settings = settings or PluginSettings.from_env()
    directory = settings.directory
    if directory.exists() and not directory.is_dir():
        raise SystemExit(f"OpenCode memory plugin path is not a directory: {directory}")

    if not directory.exists():
        if not settings.repo:
            raise SystemExit("OAT_MEMORY_PLUGIN_REPO is empty and the plugin is not installed locally")
        directory.parent.mkdir(parents=True, exist_ok=True)
        clone = _git(["clone", "--quiet", settings.repo, str(directory)], timeout=45)
        if clone.returncode != 0:
            raise SystemExit(f"Cannot clone OpenCode memory plugin: {clone.stderr.strip() or clone.stdout.strip()}")
        force_sync = True

    if (directory / ".git").is_dir():
        status = _git(["status", "--porcelain"], cwd=directory)
        if status.returncode == 0 and status.stdout.strip():
            raise SystemExit("OpenCode memory plugin checkout has local changes; refusing automatic update/build")
        _checkout_ref(settings, force_sync=force_sync)

    build_script = directory / "scripts" / "build.mjs"
    if build_script.is_file():
        build = _run(["node", str(build_script)], cwd=directory)
        if build.returncode != 0:
            raise SystemExit(f"OpenCode memory plugin build failed: {build.stderr.strip() or build.stdout.strip()}")

    required = [directory / "dist" / "v1.js", directory / "dist" / "v2.js", directory / "dist" / "cli.js"]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("OpenCode memory plugin is incomplete: " + ", ".join(missing))
    return directory


def cli_command(*args: str, force_sync: bool = False) -> list[str]:
    directory = ensure_plugin(force_sync=force_sync)
    return ["node", str(directory / "dist" / "cli.js"), *args]


if __name__ == "__main__":
    print(ensure_plugin(force_sync=True))
