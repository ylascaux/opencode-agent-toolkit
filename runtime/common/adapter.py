"""Minimal boundary between normalized agents and runtime-specific artifacts."""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, field
from typing import Mapping, Protocol

from runtime.common.normalization import NormalizedAgent


@dataclass(frozen=True)
class ArtifactPlan:
    """A pure render result shared by generation, preview, and drift checks.

    Adapters enumerate only their own obsolete files in ``stale``. Refuse
    symlinks, including ancestors, so a disposable output cannot redirect writes
    (or drift reads) into a user's project/configuration outside this boundary.
    """

    root: Path
    files: Mapping[Path, bytes] = field(default_factory=dict)
    stale: tuple[Path, ...] = ()
    notes: tuple[str, ...] = ()

    def validate(self) -> None:
        root = self.root.absolute()
        for path in (*self.files, *self.stale):
            path = path.absolute()
            try:
                relative = path.relative_to(root)
            except ValueError as exc:
                raise ValueError(f"Artifact is outside output root: {path}") from exc
            if ".." in relative.parts or not relative.parts:
                raise ValueError(f"Invalid artifact path: {path}")
            for candidate in (path, *path.parents):
                if candidate.is_symlink():
                    raise ValueError(f"Refusing symlink in generated artifact path: {candidate}")
                if candidate != path and candidate.exists() and not candidate.is_dir():
                    raise ValueError(f"Expected generated directory, found non-directory: {candidate}")
                if candidate == root:
                    break
            if path.exists() and not path.is_file():
                raise ValueError(f"Expected generated file, found non-file: {path}")
        if set(self.files) & set(self.stale):
            raise ValueError("An artifact cannot be both expected and stale")

    def changes(self) -> dict[Path, str]:
        self.validate()
        changes = {}
        for path, content in sorted(self.files.items()):
            if not path.exists():
                changes[path] = "CREATE"
            elif path.read_bytes() != content:
                changes[path] = "UPDATE"
        for path in sorted(self.stale):
            if path.exists():
                changes[path] = "DELETE"
        return changes

    def write(self) -> tuple[Path, ...]:
        changes = self.changes()
        for path, status in changes.items():
            if status == "DELETE":
                path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(self.files[path])
        return tuple(self.files)


class RuntimeAdapter(Protocol):
    """Compile one normalized agent graph into runtime-owned artifacts."""

    name: str

    def plan(self, agents: Mapping[str, NormalizedAgent]) -> ArtifactPlan:
        """Render expected artifacts without filesystem mutation."""

    def generate(self, agents: Mapping[str, NormalizedAgent]) -> tuple[Path, ...]:
        """Write deterministic runtime artifacts and return their top-level paths."""
