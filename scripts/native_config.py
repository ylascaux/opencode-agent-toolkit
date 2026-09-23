"""Small, dependency-free OpenCode renderer for the native launchers.

Canonical discovery/model tiers remain shared with Codex. Only runtime policy
belongs here: no sandbox, watchdog, approval plugin or toolkit step cap.
"""
from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

POLICY = """## Working method
Execute the user's requested work, then verify it with relevant tests. A brief
plan is useful, but do not require another approval for work already requested.
A request to plan or review only is not a request to implement.
Keep delegation small and purposeful. Reuse completed work; retry a failed child
only when there is new evidence or a recoverable error. Do not stop a healthy
session merely because it is quiet or because an arbitrary step count elapsed.
Report what was changed, what was actually tested, and what remains unverified.
Respect explicit tool denials and the user's scope. Do not expose secrets or
perform unrequested production/destructive operations.
"""
COMMANDS = {
    "auto": ("Route and execute the requested task", "Execute $ARGUMENTS using the smallest useful delegation path; verify the result."),
    "plan": ("Plan without implementing", "Plan $ARGUMENTS. Explain scope, steps, tests and important risks. Do not implement."),
    "ship": ("Implement and verify", "Implement $ARGUMENTS. Delegate implementation and relevant independent review, run tests, and report evidence."),
    "review": ("Review without changing files", "Review $ARGUMENTS. Report actionable findings with file references; do not implement fixes."),
    "debug": ("Reproduce, fix and test", "Debug $ARGUMENTS. Reproduce the problem, apply the fix, and run regression tests."),
    "architecture": ("Design from repository evidence", "Design $ARGUMENTS from repository evidence. Explain trade-offs and write documentation when requested."),
    "security": ("Review relevant security risks", "Review the security of $ARGUMENTS within the authorized scope. Prioritize verified, actionable findings."),
}
# These broad bans existed only because the old sandbox deliberately had no
# host credentials. Native tools use the user's normal Git/cloud environment.
# More specific destructive-operation denials and per-role tool denials remain.
NATIVE_COMMANDS = {
    "git fetch*", "git pull*", "git push*", "git clone*", "git ls-remote*",
    "git remote update*", "git submodule update*", "git archive --remote*",
    "git -c * fetch*", "git -c * pull*", "git -c * push*", "git -c * ls-remote*",
    "ssh *", "scp *", "sftp *", "aws *", "kubectl *",
}
RESERVED = {"description", "mode", "model", "prompt", "system", "steps", "permission", "permissions"}


def native_permissions(value: Any) -> Any:
    """Remove toolkit approval friction, not explicit denials or role boundaries."""
    if isinstance(value, dict):
        result = {key: native_permissions(item) for key, item in value.items()}
        shell = result.get("bash")
        if isinstance(shell, dict):
            for command in NATIVE_COMMANDS & shell.keys():
                shell[command] = "allow"
        return result
    return "allow" if value == "ask" else copy.deepcopy(value)


def render_config(specs: Mapping[str, Any]) -> dict:
    primary = next(name for name, spec in specs.items() if spec.mode == "primary")
    children: dict[str, list[str]] = {name: [] for name in specs}
    for name, spec in specs.items():
        for parent in spec.parents:
            children[parent].append(name)
    agents = {}
    for name, spec in sorted(specs.items()):
        delegated = sorted(children[name])
        parts = [f"# {name}\n{spec.description}"]
        if delegated:
            # Lead prompts in the old adapter contain the obsolete plan gate.
            # The native control plane uses one explicit, non-blocking policy.
            parts.append("Delegate to the smallest useful set of these children:\n" + "\n".join(
                f"- {child}: {specs[child].description}" for child in delegated
            ))
            parts.append("Give each child a concrete goal and context; consume its result before starting dependent work. Parallelize only independent tasks.")
        elif spec.prompt.strip():
            parts.append(spec.prompt.strip())
        parts.append(POLICY)
        permissions = {
            **native_permissions(spec.permissions),
            "task": {"*": "deny", **{child: "allow" for child in delegated}},
        }
        rules = []
        for action, values in permissions.items():
            resources = {"*": values} if isinstance(values, str) else values
            for resource, effect in resources.items():
                rules.append({"action": {"bash": "shell", "task": "subagent"}.get(action, action),
                              "resource": resource, "effect": effect})
        permissions = rules
        extension = copy.deepcopy(spec.extensions.get("opencode", {}))
        collisions = RESERVED & extension.keys()
        if collisions:
            raise ValueError(f"{name}: reserved OpenCode fields: {', '.join(sorted(collisions))}")
        agents[name] = {
            "description": spec.description,
            "mode": spec.mode,
            "model": f"{{env:{spec.model_env}}}",
            "system": "\n\n".join(parts),
            "permissions": permissions,
            **extension,
        }
    config = {
        "$schema": "https://opencode.ai/config.json",
        "default_agent": primary,
        "agents": agents,
        "commands": {
            name: {"description": description, "template": template, "agent": primary}
            for name, (description, template) in COMMANDS.items()
        },
        "plugins": ["opencode-mem@2.26.0"],
    }
    config["experimental"] = {"subagent_depth": 2}
    config["compaction"] = {"auto": True, "keep": {"tokens": 15000}, "buffer": 20000}
    return config


def render_files(root: Path, specs: Mapping[str, Any], skills: Mapping[str, Any]) -> dict[Path, bytes]:
    files = {
        root / "opencode.jsonc": (json.dumps(render_config(specs), indent=2) + "\n").encode()
    }
    for name, skill in sorted(skills.items()):
        files[root / ".opencode" / "skills" / name / "SKILL.md"] = (
            f"---\nname: {name}\ndescription: {json.dumps(skill.description, ensure_ascii=False)}\n---\n\n"
            "<!-- GENERATED BY opencode-agent-toolkit. DO NOT EDIT DIRECTLY. -->\n\n"
            f"{skill.prompt}\n"
        ).encode()
    return files


def write_files(files: Mapping[Path, bytes]) -> None:
    """Each self-contained config is replaced atomically, never half-written."""
    for path, content in files.items():
        if path.is_file() and path.read_bytes() == content:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
