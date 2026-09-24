"""Small ACP runner registry for toolkit V2.

OpenCode already implements ACP natively. This module only describes trusted
runner processes; protocol/session orchestration belongs in a later layer.
"""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "acp-runners.json"


@dataclass(frozen=True)
class AcpRunner:
    id: str
    command: str
    args: tuple[str, ...]
    enabled: bool = True
    trusted: bool = True

    def argv(self, environ: Mapping[str, str] | None = None) -> list[str]:
        env = os.environ if environ is None else environ
        command = self.command
        if self.id == "opencode":
            command = env.get("OPENCODE_BIN", "").strip() or command
        return [command, *self.args]

    def available(self, environ: Mapping[str, str] | None = None) -> bool:
        command = self.argv(environ)[0]
        candidate = Path(command).expanduser()
        if candidate.is_absolute() or "/" in command:
            return candidate.is_file() and os.access(candidate, os.X_OK)
        env = os.environ if environ is None else environ
        path = env.get("PATH", "")
        return shutil.which(command, path=path) is not None


def load_runners(path: Path = DEFAULT_CONFIG) -> dict[str, AcpRunner]:
    payload = json.loads(path.read_text())
    raw = payload.get("runners")
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"{path}: runners must be a non-empty object")

    runners: dict[str, AcpRunner] = {}
    for runner_id, value in raw.items():
        if not isinstance(runner_id, str) or not runner_id or not isinstance(value, dict):
            raise ValueError(f"{path}: invalid runner entry")
        command = value.get("command")
        args = value.get("args", [])
        if not isinstance(command, str) or not command.strip():
            raise ValueError(f"{path}: runner {runner_id!r} requires command")
        if not isinstance(args, list) or any(not isinstance(item, str) for item in args):
            raise ValueError(f"{path}: runner {runner_id!r} args must be strings")
        runners[runner_id] = AcpRunner(
            id=runner_id,
            command=command.strip(),
            args=tuple(args),
            enabled=bool(value.get("enabled", True)),
            trusted=bool(value.get("trusted", True)),
        )
    return runners


def enabled_runners(path: Path = DEFAULT_CONFIG) -> dict[str, AcpRunner]:
    return {name: runner for name, runner in load_runners(path).items() if runner.enabled}


def default_runner(
    runners: Mapping[str, AcpRunner],
    environ: Mapping[str, str] | None = None,
) -> AcpRunner:
    env = os.environ if environ is None else environ
    requested = env.get("OAT_ACP_DEFAULT_RUNNER", "opencode").strip() or "opencode"
    try:
        runner = runners[requested]
    except KeyError as exc:
        raise ValueError(f"unknown ACP runner: {requested}") from exc
    if not runner.enabled:
        raise ValueError(f"ACP runner is disabled: {requested}")
    return runner
