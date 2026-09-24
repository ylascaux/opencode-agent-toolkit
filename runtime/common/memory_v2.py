"""V2 memory identity/configuration primitives.

This module intentionally does not migrate or write V1 Git memory. It provides
stable project identity and namespace resolution that both local and PostgreSQL
backends can share.
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit, urlunsplit

_BACKENDS = {"legacy", "local", "postgres"}
_SAFE_PREFIX = re.compile(r"^[a-zA-Z0-9._-]+$")


def normalize_remote(remote: str) -> str:
    value = str(remote or "").strip().replace("\\", "/")
    if not value:
        return ""

    scp = re.match(r"^[^/@:]+@[^:]+:(.+)$", value)
    if scp:
        value = scp.group(1)
    elif "://" in value:
        try:
            value = urlsplit(value).path
        except ValueError:
            return ""

    value = value.strip("/").removesuffix(".git")
    parts = [part for part in value.split("/") if part]
    return "/".join(parts[-2:]) if len(parts) >= 2 else value


def _git(cwd: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


@dataclass(frozen=True)
class ProjectIdentity:
    root: Path
    name: str
    remote: str
    project_id: str
    source: str

    @property
    def namespace(self) -> str:
        return self.project_id


def resolve_project_identity(
    cwd: Path | str = ".",
    *,
    environ: Mapping[str, str] | None = None,
) -> ProjectIdentity:
    env = os.environ if environ is None else environ
    requested = Path(cwd).expanduser().resolve()
    top = _git(requested, "rev-parse", "--show-toplevel")
    root = Path(top).resolve() if top else requested
    remote = _git(root, "config", "--get", "remote.origin.url")
    remote_id = normalize_remote(remote)

    override = env.get("OAT_MEMORY_PROJECT", "").strip()
    if override:
        project_id, source = override, "override"
    elif remote_id:
        project_id, source = remote_id, "git-remote"
    else:
        project_id, source = root.name, "local-name"
    if not project_id:
        raise ValueError("cannot resolve a stable memory project id")

    return ProjectIdentity(root=root, name=root.name, remote=remote, project_id=project_id, source=source)


@dataclass(frozen=True)
class MemoryV2Config:
    backend: str
    namespace_prefix: str
    postgres_dsn: str
    local_path: Path

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "MemoryV2Config":
        env = os.environ if environ is None else environ
        backend = env.get("OAT_MEMORY_BACKEND", "local").strip().lower() or "legacy"
        if backend not in _BACKENDS:
            raise ValueError(f"OAT_MEMORY_BACKEND must be one of: {', '.join(sorted(_BACKENDS))}")
        prefix = env.get("OAT_MEMORY_NAMESPACE_PREFIX", "oat").strip() or "oat"
        if not _SAFE_PREFIX.fullmatch(prefix):
            raise ValueError("OAT_MEMORY_NAMESPACE_PREFIX contains unsupported characters")
        dsn = env.get("OAT_MEMORY_POSTGRES_DSN", "").strip()
        if backend == "postgres" and not dsn:
            raise ValueError("OAT_MEMORY_POSTGRES_DSN is required for postgres memory")
        data_home = Path(env.get("XDG_DATA_HOME") or Path.home() / ".local/share")
        local_path = Path(
            env.get("OAT_MEMORY_LOCAL_PATH")
            or data_home / "opencode-agent-toolkit" / "memory-v2.sqlite"
        ).expanduser()
        return cls(
            backend=backend,
            namespace_prefix=prefix,
            postgres_dsn=dsn,
            local_path=local_path,
        )

    def namespace_for(self, identity: ProjectIdentity) -> str:
        return f"{self.namespace_prefix}:project:{identity.project_id}"

    def global_namespace(self) -> str:
        return f"{self.namespace_prefix}:user:default"

    @property
    def shared(self) -> bool:
        return self.backend == "postgres"

    def masked_dsn(self) -> str:
        if not self.postgres_dsn:
            return ""
        try:
            parsed = urlsplit(self.postgres_dsn)
        except ValueError:
            return "<configured>"
        if not parsed.scheme:
            return "<configured>"
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        user = parsed.username or ""
        auth = f"{user}:***@" if user else ""
        path = parsed.path or ""
        return urlunsplit((parsed.scheme, f"{auth}{host}{port}", path, "", ""))
