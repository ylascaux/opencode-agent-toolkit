#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.common.normalization import (  # noqa: E402
    DEFAULTS_DIR,
    NormalizedAgent,
    children_by_parent,
    load_normalized_agents,
    model_profiles,
    model_tiers,
)
from runtime.opencode.adapter import (  # noqa: E402
    GENERATED_DIR,
    GENERATED_PROMPTS_DIR,
    OpenCodeAdapter,
    task_permissions,
    v1_permissions,
    v2_permissions,
    write_generated_sources,
)

AgentSpec = NormalizedAgent
load_agents = load_normalized_agents


def main() -> int:
    specs = load_agents()
    children = children_by_parent(specs)
    print(f"{len(specs)} agents")
    for name in sorted(specs):
        spec = specs[name]
        parents = ",".join(spec.parents) or "-"
        delegated = ",".join(children[name]) or "-"
        print(
            f"{name:<24} tier={spec.tier:<6} model={spec.model_env:<28} "
            f"parents={parents} children={delegated}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
