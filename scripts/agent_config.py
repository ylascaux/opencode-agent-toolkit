#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
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

GENERATED_DIR = ROOT / ".generated"
GENERATED_PROMPTS_DIR = GENERATED_DIR / "prompts"

ACTION_MAP = {"bash": "shell", "task": "subagent"}
PROMPT_ACTION_LABELS = {"bash": "bash / shell", "task": "task / subagent"}
AgentSpec = NormalizedAgent
load_agents = load_normalized_agents


def task_permissions(name: str, specs: dict[str, NormalizedAgent]) -> dict[str, str]:
    children = children_by_parent(specs)[name]
    return {"*": "deny", **{child: "allow" for child in children}}


def v1_permissions(name: str, specs: dict[str, NormalizedAgent]) -> dict:
    return {"task": task_permissions(name, specs), **copy.deepcopy(specs[name].permissions)}


def v2_permissions(name: str, specs: dict[str, NormalizedAgent]) -> list[dict]:
    rules: list[dict] = []
    for key, value in v1_permissions(name, specs).items():
        action = ACTION_MAP.get(key, key)
        if isinstance(value, str):
            rules.append({"action": action, "resource": "*", "effect": value})
        else:
            for resource, effect in value.items():
                rules.append({"action": action, "resource": resource, "effect": effect})
    return rules


def render_capabilities(name: str, specs: dict[str, NormalizedAgent]) -> str:
    grouped: dict[str, dict[str, list[str]]] = {
        effect: {} for effect in ("allow", "ask", "deny")
    }
    for action, value in v1_permissions(name, specs).items():
        label = PROMPT_ACTION_LABELS.get(action, action)
        rules = {"*": value} if isinstance(value, str) else value
        for resource, effect in rules.items():
            grouped[effect].setdefault(label, []).append(resource)

    lines = [
        "## Effective capabilities",
        "This capability map is generated from the same effective permissions used to build the OpenCode configuration; do not maintain a separate manual tool list.",
        "`ALLOW` may be used without approval, `ASK` requires runtime/user approval, and `DENY` must never be attempted. Resource-specific rules refine wildcard baselines; obey the most specific runtime rule.",
        "The runtime may expose fewer tools than this permission map. Never invent, probe, or assume an undeclared tool exists, and never bypass a denied capability through another command or tool.",
        "Delegation is limited to the explicitly allowed `task / subagent` resources below.",
    ]
    for effect, heading in (("allow", "ALLOW"), ("ask", "ASK"), ("deny", "DENY")):
        lines.extend(["", f"### {heading}"])
        actions = grouped[effect]
        if not actions:
            lines.append("- None.")
            continue
        for action, resources in actions.items():
            rendered = ", ".join(f"`{resource}`" for resource in resources)
            lines.append(f"- `{action}`: {rendered}")
    return "\n".join(lines)


def render_prompt(spec: NormalizedAgent, specs: dict[str, NormalizedAgent]) -> str:
    default_prompt = (DEFAULTS_DIR / "prompt.md").read_text().strip()
    parts = [f"# Role\n{spec.description}"]
    if spec.prompt:
        parts.append(spec.prompt)
    if default_prompt:
        parts.append(default_prompt)
    parts.append(render_capabilities(spec.name, specs))
    return "\n\n".join(parts).rstrip() + "\n"


def write_generated_sources(specs: dict[str, NormalizedAgent]) -> None:
    GENERATED_PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    for old in GENERATED_PROMPTS_DIR.glob("*.md"):
        old.unlink()
    for name, spec in specs.items():
        (GENERATED_PROMPTS_DIR / f"{name}.md").write_text(render_prompt(spec, specs))

    children = children_by_parent(specs)
    manifest = {}
    for name, spec in specs.items():
        manifest[name] = {
            "description": spec.description,
            "mode": spec.mode,
            "model_env": spec.model_env,
            "tier": spec.tier,
            "model_profile": spec.model_profile,
            "steps": spec.steps,
            "parents": list(spec.parents),
            "children": children[name],
            "source": f"agents/{name}",
        }
    GENERATED_DIR.mkdir(exist_ok=True)
    (GENERATED_DIR / "agents.json").write_text(json.dumps(manifest, indent=2) + "\n")


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
