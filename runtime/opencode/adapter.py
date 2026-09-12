"""OpenCode V1/V2 rendering from the runtime-neutral normalized agent graph."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Mapping

from runtime.common.normalization import DEFAULTS_DIR, NormalizedAgent, children_by_parent
from runtime.common.adapter import ArtifactPlan

ROOT = Path(__file__).resolve().parents[2]
GENERATED_DIR = ROOT / ".generated"
GENERATED_PROMPTS_DIR = GENERATED_DIR / "prompts"

ACTION_MAP = {"bash": "shell", "task": "subagent"}
PROMPT_ACTION_LABELS = {"bash": "bash / shell", "task": "task / subagent"}

COMMANDS = {
    "auto": (
        "Automatically classify, plan and route a task",
        "Route $ARGUMENTS using the minimum sufficient path. Use the routing contract, keep delegation depth <= 2, escalate only on risk/uncertainty/disagreement. If the task can mutate state, gather only enough evidence to produce a concrete plan, surface it to the user, end with PLAN_APPROVAL_REQUIRED, and stop until explicit approval. After approval, execute the approved path and finish with evidence and residual risk.",
    ),
    "plan": (
        "Create a user-approvable execution plan without implementing it",
        "Plan $ARGUMENTS. Route read-only discovery/planning through the minimum sufficient path, include goal/scope, affected files/components, ordered steps, validation/tests, rollback, and delegated agents/gates. Do not mutate state. End with PLAN_APPROVAL_REQUIRED.",
    ),
    "ship": (
        "Plan first, then implement with tests, independent review and adaptive security gates",
        "Ship $ARGUMENTS. Classify risk first and delegate planning/delivery to orchestrator. Before any mutation, surface the concrete implementation plan and end with PLAN_APPROVAL_REQUIRED. Only after explicit user approval may orchestrator execute the approved scope, require relevant tests and independent review, add only security gates matching the changed attack surface, and audit non-trivial completion evidence. Material scope deviations require PLAN_REAPPROVAL_REQUIRED.",
    ),
    "review": (
        "Run independent adaptive review",
        "Review $ARGUMENTS via review-lead. Select only review dimensions touched by the change, deduplicate findings, arbitrate material disagreement, and audit weak completion claims.",
    ),
    "architecture": (
        "Design architecture with approval before artifact mutation",
        "Design $ARGUMENTS via platform-architect. Gather evidence and stabilize the design first. If durable documentation or another artifact will be created/updated, surface the write/migration plan and end with PLAN_APPROVAL_REQUIRED before mutation. After explicit approval, have platform-architect delegate writing to docs-writer. Once the artifact exists, independently review it via review-lead against repository evidence. When trust boundaries, IAM, public exposure, secrets, or infrastructure-security posture materially change, run security-lead in parallel with review-lead. Synthesize only after required reviews complete; report evidence, trade-offs, rejected alternatives, migration/rollback and residual risks. Never let the producing path self-review.",
    ),
    "architecture-review": (
        "Independently review an existing architecture artifact",
        "Independently review $ARGUMENTS via review-lead. Re-establish repository evidence with project-scanner when needed, select only relevant platform and security dimensions, do not treat the producer handoff as proof, and report contradictions, missing assumptions, rollback gaps, residual risks and confidence.",
    ),
    "security": (
        "Run adaptive defense-in-depth security review",
        "Security-review $ARGUMENTS via security-lead. Select only relevant threat-model/AppSec/IaC/supply-chain/secrets gates; pentest only explicitly authorized runtime scope. Deduplicate, rank and verify findings.",
    ),
    "debug": (
        "Evidence-first debugging with approval before fixes",
        "Debug $ARGUMENTS via orchestrator. Start with read-only reproduction/evidence and the affected specialist. Before applying a fix, surface the proposed fix/regression-test plan and end with PLAN_APPROVAL_REQUIRED. After explicit approval, implement the approved fix, add regression coverage, independently review it and add security gates if a trust boundary changes. Material deviations require PLAN_REAPPROVAL_REQUIRED.",
    ),
    "incident": (
        "Investigate an incident and gate remediation behind a plan",
        "Investigate $ARGUMENTS via orchestrator using evidence-first debugging plus SRE/observability and affected domain specialists. Separate facts from hypotheses and identify blast radius. Investigation may stay read-only; before remediation or rollback mutation, surface the mitigation plan and end with PLAN_APPROVAL_REQUIRED. Execute only after explicit approval and re-request approval for material scope changes.",
    ),
    "cost": (
        "Analyze platform cost and cost-performance trade-offs",
        "Analyze $ARGUMENTS via platform-architect using FinOps plus only relevant AWS/Kubernetes/database/networking/performance perspectives. State source data, assumptions, trade-offs and confidence.",
    ),
}

# V1 intentionally has no plan-approval workflow. Keep command wording aligned
# with the V1 prompt/runtime configuration so commands do not recreate a pause.
V1_COMMANDS = {
    "auto": (
        "Automatically classify, plan and route a task",
        "Route $ARGUMENTS using the minimum sufficient path. Use the routing contract, keep delegation depth <= 2, escalate only on risk/uncertainty/disagreement. Execute the requested path and finish with evidence and residual risk.",
    ),
    "plan": (
        "Create an execution plan without implementing it",
        "Plan $ARGUMENTS. Route discovery/planning through the minimum sufficient path, include goal/scope, affected files/components, ordered steps, validation/tests, rollback, and delegated agents/gates. Do not implement the plan.",
    ),
    "ship": (
        "Implement with tests, independent review and adaptive security gates",
        "Ship $ARGUMENTS. Classify risk first and delegate delivery to orchestrator, require relevant tests and independent review, add only security gates matching the changed attack surface, and audit non-trivial completion evidence.",
    ),
    "architecture": (
        "Design architecture and produce durable artifacts when requested",
        "Design $ARGUMENTS via platform-architect. Gather evidence and stabilize the design, then have platform-architect delegate durable writing to docs-writer when requested. Once the artifact exists, independently review it via review-lead against repository evidence. When trust boundaries, IAM, public exposure, secrets, or infrastructure-security posture materially change, run security-lead in parallel with review-lead. Synthesize only after required reviews complete; report evidence, trade-offs, rejected alternatives, migration/rollback and residual risks. Never let the producing path self-review.",
    ),
    "debug": (
        "Evidence-first debugging with regression coverage",
        "Debug $ARGUMENTS via orchestrator. Start with read-only reproduction/evidence and the affected specialist, then apply the fix, add regression coverage, independently review it and add security gates if a trust boundary changes.",
    ),
    "incident": (
        "Investigate and remediate an incident",
        "Investigate $ARGUMENTS via orchestrator using evidence-first debugging plus SRE/observability and affected domain specialists. Separate facts from hypotheses, identify blast radius, then execute the required remediation or rollback and report the evidence.",
    ),
}

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

    def plan(self, specs: Mapping[str, NormalizedAgent]) -> ArtifactPlan:
        source_plan = self.source_plan(specs)
        files = dict(source_plan.files)
        outputs = (
            (self.root / "opencode.jsonc", self.build(specs, v2=False)),
            (self.root / "opencode.v2.jsonc", self.build(specs, v2=True)),
        )
        for path, data in outputs:
            files[path] = (json.dumps(data, indent=2) + "\n").encode()
        return ArtifactPlan(self.root, files, source_plan.stale)

    def generate(self, specs: Mapping[str, NormalizedAgent]) -> tuple[Path, ...]:
        self.plan(specs).write()
        return (self.root / "opencode.jsonc", self.root / "opencode.v2.jsonc")


def write_generated_sources(specs: Mapping[str, NormalizedAgent]) -> None:
    """Compatibility helper for callers that only need OpenCode prompt artifacts."""
    OpenCodeAdapter().write_generated_sources(specs)
