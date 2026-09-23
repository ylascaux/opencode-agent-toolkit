"""OpenCode V1/V2 rendering from the runtime-neutral normalized agent graph."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Mapping

from runtime.common.normalization import DEFAULTS_DIR, NormalizedAgent, NormalizedSkill, children_by_parent
from runtime.common.adapter import ArtifactPlan

ROOT = Path(__file__).resolve().parents[2]
GENERATED_DIR = ROOT / ".generated"
GENERATED_PROMPTS_DIR = GENERATED_DIR / "prompts"

ACTION_MAP = {"bash": "shell", "task": "subagent"}
PROMPT_ACTION_LABELS = {"bash": "bash / shell", "task": "task / subagent"}

COMMANDS = {
    "auto": (
        "Route a task through the minimum sufficient core agents",
        "Route $ARGUMENTS using the active core catalog. Keep delegation depth <= 2, prefer one path over a committee, and obey the effective runtime approval mode rather than inventing an extra approval pause.",
    ),
    "plan": (
        "Create an execution plan without implementing it",
        "Plan $ARGUMENTS. Use repository evidence and research only when needed. Include scope, affected components, ordered steps, validation, rollback and the minimal core-agent route. Do not implement the plan.",
    ),
    "ship": (
        "Implement with tests and independent review",
        "Ship $ARGUMENTS via orchestrator. Use builder/debugger/tester only as needed, require reviewer for independent final review, and add security-lead only when a security boundary materially changes.",
    ),
    "review": (
        "Run independent correctness review",
        "Review $ARGUMENTS via reviewer. Re-check the primary repository evidence, report findings by severity, and request security-lead or research-runner only when that adds distinct evidence.",
    ),
    "architecture": (
        "Design platform/application architecture with independent review",
        "Design $ARGUMENTS via platform-architect. Treat cloud, Kubernetes, Terraform, database, networking, SRE, observability and FinOps as architecture competencies rather than separate agents. Route implementation through orchestrator if requested, then use reviewer independently and security-lead when trust boundaries or exposure change.",
    ),
    "architecture-review": (
        "Independently review an architecture artifact",
        "Independently review $ARGUMENTS via reviewer using direct repository evidence. Add platform-architect for unresolved design trade-offs and security-lead for material trust/IAM/exposure concerns.",
    ),
    "security": (
        "Run integrated security review",
        "Security-review $ARGUMENTS via security-lead. Cover only materially relevant application, IAM, infrastructure, secrets, supply-chain and exposure surfaces; keep runtime testing authorized and non-destructive.",
    ),
    "debug": (
        "Evidence-first debugging with regression coverage",
        "Debug $ARGUMENTS via orchestrator. Use debugger for causal diagnosis, builder for the smallest fix, tester for regression coverage when useful, then reviewer independently.",
    ),
    "incident": (
        "Investigate and remediate an incident",
        "Investigate $ARGUMENTS via orchestrator. Separate facts from hypotheses, identify blast radius, use debugger/research/security only when needed, apply the smallest justified remediation, and finish with reviewer evidence.",
    ),
    "cost": (
        "Analyze platform cost and cost-performance trade-offs",
        "Analyze $ARGUMENTS via platform-architect. Use research-runner when current pricing or provider facts are needed. State source data, assumptions, trade-offs and confidence.",
    ),
}

# V1 compatibility artifacts reuse the same small-agent command language.
V1_COMMANDS = {}

GENERATED_AGENT_KEYS = {
    "description", "mode", "model", "prompt", "system", "steps", "permission", "permissions",
}

V2_COMPACTION = {
    "auto": True,
    "keep": {"tokens": 15000},
    "buffer": 20000,
}


def task_permissions(name: str, specs: Mapping[str, NormalizedAgent]) -> dict[str, str]:
    children = children_by_parent(dict(specs))[name]
    return {"*": "deny", **{child: "allow" for child in children}}


def v1_permissions(name: str, specs: Mapping[str, NormalizedAgent]) -> dict:
    return {"task": task_permissions(name, specs), **copy.deepcopy(specs[name].permissions)}


def v2_permissions(name: str, specs: Mapping[str, NormalizedAgent]) -> list[dict]:
    rules: list[dict] = []
    for key, value in v1_permissions(name, specs).items():
        action = ACTION_MAP.get(key, key)
        if isinstance(value, str):
            rules.append({"action": action, "resource": "*", "effect": value})
        else:
            for resource, effect in value.items():
                rules.append({"action": action, "resource": resource, "effect": effect})
    return rules


class OpenCodeAdapter:
    """Render the existing OpenCode V1/V2 artifacts from normalized agents."""

    name = "opencode"

    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        self.generated_dir = root / ".generated"
        self.generated_prompts_dir = self.generated_dir / "prompts"
        self.skills_dir = root / ".opencode" / "skills"

    @staticmethod
    def render_skill(skill: NormalizedSkill) -> bytes:
        """Render OpenCode's documented local SKILL.md shape from normalized data."""
        return (
            "---\n"
            f"name: {skill.name}\n"
            f"description: {json.dumps(skill.description, ensure_ascii=False)}\n"
            "---\n\n"
            "<!-- GENERATED BY opencode-agent-toolkit. DO NOT EDIT DIRECTLY. -->\n\n"
            f"{skill.prompt}\n"
        ).encode()

    def render_capabilities(self, name: str, specs: Mapping[str, NormalizedAgent]) -> str:
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

    def render_prompt(self, spec: NormalizedAgent, specs: Mapping[str, NormalizedAgent]) -> str:
        default_prompt = (self.root / "agents" / "_defaults" / "prompt.md").read_text().strip()
        parts = [f"# Role\n{spec.description}"]
        if spec.prompt:
            parts.append(spec.prompt)
        if default_prompt:
            parts.append(default_prompt)
        parts.append(self.render_capabilities(spec.name, specs))
        return "\n\n".join(parts).rstrip() + "\n"

    def source_plan(self, specs: Mapping[str, NormalizedAgent]) -> ArtifactPlan:
        files = {}
        for name, spec in specs.items():
            files[self.generated_prompts_dir / f"{name}.md"] = self.render_prompt(spec, specs).encode()

        children = children_by_parent(dict(specs))
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
        files[self.generated_dir / "agents.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
        stale = tuple(path for path in self.generated_prompts_dir.glob("*.md") if path not in files)
        return ArtifactPlan(self.root, files, stale)

    def write_generated_sources(self, specs: Mapping[str, NormalizedAgent]) -> None:
        self.source_plan(specs).write()

    def agent_entry(
        self, name: str, specs: Mapping[str, NormalizedAgent], *, v2: bool
    ) -> dict:
        spec = specs[name]
        opencode = spec.extensions["opencode"]
        collisions = GENERATED_AGENT_KEYS & set(opencode)
        if collisions:
            raise SystemExit(
                f"{name}: opencode cannot override generated keys: {', '.join(sorted(collisions))}"
            )
        entry = {
            "description": spec.description,
            "mode": spec.mode,
            "model": f"{{env:{spec.model_env}}}",
            ("system" if v2 else "prompt"): f"{{file:./.generated/prompts{'-v1' if not v2 else ''}/{name}.md}}",
            "steps": spec.steps,
            ("permissions" if v2 else "permission"): (
                v2_permissions(name, specs) if v2 else v1_permissions(name, specs)
            ),
        }
        entry.update(opencode)
        return entry

    def build(self, specs: Mapping[str, NormalizedAgent], *, v2: bool) -> dict:
        primary = next(name for name, spec in specs.items() if spec.mode == "primary")
        agents = {name: self.agent_entry(name, specs, v2=v2) for name in sorted(specs)}
        command_specs = COMMANDS if v2 else {**COMMANDS, **V1_COMMANDS}
        commands = {
            name: {"description": desc, "template": template, "agent": primary}
            for name, (desc, template) in command_specs.items()
        }
        if v2:
            return {
                "$schema": "https://opencode.ai/config.json",
                "default_agent": primary,
                "compaction": V2_COMPACTION,
                "shell": str(self.root / "scripts" / "sandbox-shell-v2"),
                "agents": agents,
                "commands": commands,
                "plugins": [],
                "experimental": {"subagent_depth": 2},
            }
        return {
            "$schema": "https://opencode.ai/config.json",
            "default_agent": primary,
            "subagent_depth": 2,
            "agent": agents,
            "command": commands,
            "plugin": ["./runtime/plugins/sandbox-v1.js"],
        }

    def plan(
        self, specs: Mapping[str, NormalizedAgent], skills: Mapping[str, NormalizedSkill] | None = None
    ) -> ArtifactPlan:
        skills = skills or {}
        source_plan = self.source_plan(specs)
        files = dict(source_plan.files)
        outputs = (
            (self.root / "opencode.jsonc", self.build(specs, v2=False)),
            (self.root / "opencode.v2.jsonc", self.build(specs, v2=True)),
        )
        for path, data in outputs:
            files[path] = (json.dumps(data, indent=2) + "\n").encode()
        for name in sorted(skills):
            files[self.skills_dir / name / "SKILL.md"] = self.render_skill(skills[name])
        ArtifactPlan(self.root, files).validate()
        stale = list(source_plan.stale)
        if self.skills_dir.exists():
            for path in self.skills_dir.glob("*/SKILL.md"):
                if path in files:
                    continue
                ArtifactPlan(self.root, {path: b""}).validate()
                with path.open("rb") as stream:
                    header = stream.read(512)
                if b"GENERATED BY opencode-agent-toolkit" in header:
                    stale.append(path)
        return ArtifactPlan(self.root, files, tuple(sorted(stale)))

    def generate(
        self, specs: Mapping[str, NormalizedAgent], skills: Mapping[str, NormalizedSkill] | None = None
    ) -> tuple[Path, ...]:
        self.plan(specs, skills).write()
        return (self.root / "opencode.jsonc", self.root / "opencode.v2.jsonc")


def write_generated_sources(specs: Mapping[str, NormalizedAgent]) -> None:
    """Compatibility helper for callers that only need OpenCode prompt artifacts."""
    OpenCodeAdapter().write_generated_sources(specs)
