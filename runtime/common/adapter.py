"""Minimal boundary between normalized agents and runtime-specific artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Protocol

from runtime.common.normalization import NormalizedAgent


class RuntimeAdapter(Protocol):
    """Compile one normalized agent graph into runtime-owned artifacts."""

    name: str

    def generate(self, agents: Mapping[str, NormalizedAgent]) -> tuple[Path, ...]:
        """Write deterministic runtime artifacts and return their top-level paths."""
