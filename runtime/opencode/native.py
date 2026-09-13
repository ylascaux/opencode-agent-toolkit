"""Native rendering: canonical agents/skills, no container or supervision plugins.

The historical adapter remains available to existing consumers and fixtures.
Codex keeps its own adapter and synchronization lifecycle unchanged.
"""
from __future__ import annotations

import copy
import json
import os
import re
from dataclasses import replace

from runtime.common.adapter import ArtifactPlan
from runtime.common.normalization import deep_merge
from runtime.opencode.adapter import COMMANDS, V1_COMMANDS, OpenCodeAdapter

# These were transport restrictions, not permissions inherent to an agent's role.
REMOTE_RESTRICTIONS = {
    "git fetch*", "git pull*", "git push*", "git clone*", "git ls-remote*",
    "git remote update*", "git submodule update*", "git archive --remote*",
    "git -c * fetch*", "git -c * pull*", "git -c * push*", "git -c * ls-remote*",
    "ssh *", "scp *", "sftp *",
}
LEGACY_SECTIONS = {
    "non-interactive execution", "remote git access is manual-only",
    "cloud diagnostics are manual-only", "architecture delivery workflow",
}
NATIVE_POLICY = """## Native execution
- Execute the user's requested scope without a second toolkit plan-approval pause. A request for a plan alone remains read-only.
- Use the normal host tools and shell. Prefer non-interactive commands; ordinary shell composition is supported.
- Respect explicit role permissions, repository instructions and the user's authorization. Do not read credentials or silently broaden scope.
- Design before writing; independently review completed changes. Never use the producing agent as its only reviewer.
- Reuse completed child results. Missing progress events or a quiet orchestrator are not reasons to kill, cancel or restart sessions.
- Report provider/authentication failures directly; do not hide them behind retries or additional delegations.
"""


def native_prompt(text: str) -> str:
    """Remove obsolete transport/approval sections from the rendered copy only."""
    kept = []
    for section in re.split(r"(?=^## )", text, flags=re.MULTILINE):
        heading = section.splitlines()[0].removeprefix("## ").strip().lower() if section else ""
        if heading in LEGACY_SECTIONS or "plan approval" in heading:
            continue
        if "PLAN_APPROVAL_REQUIRED" in section or "PLAN_REAPPROVAL_REQUIRED" in section:
            continue
        kept.append(section)
    return "".join(kept).strip()


class NativeOpenCodeAdapter(OpenCodeAdapter):
    def native_specs(self, specs):
        defaults = json.loads((self.root / "agents/_defaults/permissions.json").read_text())
        defaults = copy.deepcopy(defaults)
        defaults["edit"] = "allow"
        defaults["skill"] = "allow"
        shell = defaults.get("bash", {})
        if isinstance(shell, dict):
            shell["*"] = "allow"
            for key in REMOTE_RESTRICTIONS:
                shell.pop(key, None)
            # Cloud access is no longer blanket-denied; destructive rules remain.
            shell["aws *"] = "ask"
            shell["kubectl *"] = "ask"
        result = {}
        for name, spec in specs.items():
            local = json.loads((spec.path / "permissions.json").read_text())
            result[name] = replace(spec, permissions=deep_merge(defaults, local))
        return result

    def render_prompt(self, spec, specs):
        defaults = native_prompt((self.root / "agents/_defaults/prompt.md").read_text())
        parallel = os.getenv("MAX_PARALLEL_SUBAGENTS", "3")
        if not parallel.isdigit() or int(parallel) < 1:
            raise SystemExit("MAX_PARALLEL_SUBAGENTS must be a positive integer")
        parts = [f"# Role\n{spec.description}", native_prompt(spec.prompt), defaults,
                 NATIVE_POLICY + f"- Run at most {parallel} independent children in parallel; this is a scheduling instruction, not a cancellation watchdog.\n",
                 self.render_capabilities(spec.name, specs)]
        return "\n\n".join(part.strip() for part in parts if part.strip()) + "\n"

    def build(self, specs, *, v2):
        data = super().build(specs, v2=v2)
        data.pop("shell", None)
        data["plugins" if v2 else "plugin"] = []
        for agent in data["agents" if v2 else "agent"].values():
            # Do not cap completion with the historical 8/16-step toolkit limits.
            agent.pop("steps", None)
        data["commands" if v2 else "command"] = {
            name: {"description": desc, "template": template, "agent": data["default_agent"]}
            for name, (desc, template) in {**COMMANDS, **V1_COMMANDS}.items()
        }
        return data

    def plan(self, specs, skills=None):
        plan = super().plan(self.native_specs(specs), skills)
        files = dict(plan.files)
        v1_dir = self.generated_dir / "prompts-v1"
        # V1 injects memory at runtime; V2 receives rendered per-project memory.
        # Copy before apply-memory so V1 does not receive it twice.
        for path, content in plan.files.items():
            if path.parent == self.generated_prompts_dir and path.suffix == ".md":
                files[v1_dir / path.name] = content
        stale = tuple(sorted(set(plan.stale) | {p for p in v1_dir.glob("*.md") if p not in files}))
        return ArtifactPlan(self.root, files, stale)
