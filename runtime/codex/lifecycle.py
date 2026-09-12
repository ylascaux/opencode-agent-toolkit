"""Safe project-local lifecycle for the generated Codex agent bundle.

This module intentionally reads ``.generated/codex`` rather than canonical
``agents/`` definitions.  Generation remains the CodexAdapter's responsibility;
this layer only plans and applies project-local installation state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
from typing import Iterable


MANIFEST = ".opencode-agent-toolkit.json"
MANIFEST_VERSION = 1
MCP_SECTION = "opencode_agent_toolkit_memory"
MCP_HEADER = f"[mcp_servers.{MCP_SECTION}]"
MCP_COMMENT = "# Managed by opencode-agent-toolkit. Remove with: oc codex uninstall"


class LifecycleError(ValueError):
    """A safe lifecycle operation could not be planned."""


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _check_directory(path: Path, *, label: str, create_ok: bool = True) -> None:
    """Reject symlinks and non-directory ancestors below a project boundary."""
    if path.is_symlink():
        raise LifecycleError(f"Refusing symlinked {label}: {path}")
    if path.exists() and not path.is_dir():
        raise LifecycleError(f"Expected {label} directory, found non-directory: {path}")
    if not create_ok and not path.exists():
        raise LifecycleError(f"Missing {label} directory: {path}")


def _safe_child(parent: Path, relative: str) -> Path:
    candidate = parent / relative
    try:
        candidate.relative_to(parent)
    except ValueError as exc:
        raise LifecycleError(f"Artifact path escapes project: {relative}") from exc
    if ".." in Path(relative).parts or Path(relative).is_absolute():
        raise LifecycleError(f"Invalid managed artifact path: {relative}")
    return candidate


def _validate_project(project: Path) -> Path:
    project = project.expanduser().absolute()
    if not project.exists() or not project.is_dir():
        raise LifecycleError(f"Target project is not a directory: {project}")
    if project.is_symlink():
        raise LifecycleError(f"Refusing symlinked target project: {project}")
    return project.resolve()


def _read_manifest(codex_dir: Path) -> dict | None:
    path = codex_dir / MANIFEST
    if path.is_symlink():
        raise LifecycleError(f"Refusing symlinked ownership manifest: {path}")
    if not path.exists():
        return None
    if not path.is_file():
        raise LifecycleError(f"Ownership manifest is not a regular file: {path}")
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise LifecycleError(f"Invalid ownership manifest: {path}") from exc
    if not isinstance(value, dict) or set(value) - {"version", "agents", "memory_mcp"} or value.get("version") != MANIFEST_VERSION:
        raise LifecycleError(f"Unsupported ownership manifest: {path}")
    agents = value.get("agents", {})
    if not isinstance(agents, dict) or not all(
        isinstance(key, str)
        and Path(key).parts == ("agents", Path(key).name)
        and bool(re.fullmatch(r"[a-z0-9][a-z0-9-]*\.toml", Path(key).name))
        and isinstance(value, str)
        and re.fullmatch(r"[0-9a-f]{64}", value)
        for key, value in agents.items()
    ):
        raise LifecycleError(f"Invalid managed agents in manifest: {path}")
    memory = value.get("memory_mcp")
    if memory is not None and not isinstance(memory, dict):
        raise LifecycleError(f"Invalid memory MCP state in manifest: {path}")
    if memory is not None and (
        set(memory) != {"managed", "config", "section", "hash"}
        or memory.get("managed") is not True
        or memory.get("config") != "config.toml"
        or memory.get("section") != MCP_SECTION
        or not isinstance(memory.get("hash"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", memory["hash"])
    ):
        raise LifecycleError(f"Invalid memory MCP state in manifest: {path}")
    return value


def _bundle_agents(root: Path) -> dict[str, bytes]:
    bundle = root / ".generated" / "codex"
    agents = bundle / "agents"
    _check_directory(bundle, label="generated Codex bundle", create_ok=False)
    _check_directory(agents, label="generated Codex agents", create_ok=False)
    result: dict[str, bytes] = {}
    for path in sorted(agents.glob("*.toml")):
        if path.is_symlink() or not path.is_file():
            raise LifecycleError(f"Refusing non-regular generated agent: {path}")
        result[f"agents/{path.name}"] = path.read_bytes()
    if not result:
        raise LifecycleError(f"No generated Codex TOML agents found in {agents}; run: oc sync codex")
    return result


def _mcp_block(root: Path, project: Path) -> bytes:
    launcher = root / "scripts" / "memory-mcp"
    if launcher.is_symlink() or not launcher.is_file():
        raise LifecycleError(f"Memory MCP launcher is unavailable: {launcher}")
    # JSON strings are legal TOML basic strings and avoid a bespoke escaping rule.
    return (
        f"{MCP_COMMENT}\n{MCP_HEADER}\n"
        f"command = {json.dumps(str(launcher))}\n"
        f"args = [{json.dumps('--cwd')}, {json.dumps(str(project))}]\n"
    ).encode()


def _mcp_bounds(content: bytes) -> tuple[int, int] | None:
    """Return the precise owned TOML table, never a broad regex replacement."""
    lines = content.splitlines(keepends=True)
    start = None
    offset = 0
    previous_plain = None
    previous_offset = None
    for line in lines:
        plain = line.decode("utf-8", "strict").strip()
        if plain == MCP_HEADER:
            if start is not None:
                raise LifecycleError("Duplicate managed memory MCP tables")
            start = previous_offset if previous_plain == MCP_COMMENT else offset
        elif start is not None and plain.startswith("["):
            return start, offset
        previous_plain = plain
        previous_offset = offset
        offset += len(line)
    return (start, len(content)) if start is not None else None


def _config_with_block(config: Path, block: bytes, *, owned_hash: str | None) -> tuple[bytes, str]:
    if config.is_symlink():
        raise LifecycleError(f"Refusing symlinked Codex config: {config}")
    if config.exists() and not config.is_file():
        raise LifecycleError(f"Codex config is not a regular file: {config}")
    original = config.read_bytes() if config.exists() else b""
    try:
        parsed = tomllib.loads(original.decode()) if original else {}
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise LifecycleError(f"Cannot safely update invalid Codex TOML: {config}") from exc
    servers = parsed.get("mcp_servers", {})
    if servers and not isinstance(servers, dict):
        raise LifecycleError(f"Cannot safely update MCP configuration: {config}")
    exists = isinstance(servers, dict) and MCP_SECTION in servers
    bounds = _mcp_bounds(original) if original else None
    if exists and bounds is None:
        raise LifecycleError(f"Cannot safely isolate existing MCP table: {config}")
    if exists and owned_hash is None:
        raise LifecycleError(f"CONFLICT {config}: memory MCP table is user-owned")
    if bounds is not None:
        start, end = bounds
        if owned_hash is not None and digest(original[start:end]) != owned_hash:
            raise LifecycleError(f"Managed MCP table was modified; preserving it: {config}")
        return original[:start] + block + original[end:], "UPDATE"
    separator = b"" if not original or original.endswith(b"\n") else b"\n"
    return original + separator + block, "CREATE"


def _remove_mcp_block(config: Path, expected_hash: str) -> bytes:
    if config.is_symlink() or not config.is_file():
        raise LifecycleError(f"Managed MCP config is missing or unsafe: {config}")
    original = config.read_bytes()
    bounds = _mcp_bounds(original)
    if bounds is None:
        raise LifecycleError(f"Managed MCP table is missing: {config}")
    start, end = bounds
    block = original[start:end]
    if digest(block) != expected_hash:
        raise LifecycleError(f"Managed MCP table was modified; preserving it: {config}")
    return original[:start] + original[end:]


@dataclass
class Change:
    action: str
    path: Path
    content: bytes | None = None


@dataclass
class CodexInstallPlan:
    project: Path
    changes: list[Change] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    def add(self, action: str, path: Path, content: bytes | None = None) -> None:
        self.changes.append(Change(action, path, content))

    def show(self) -> None:
        for change in self.changes:
            print(f"{change.action:<7} {change.path.relative_to(self.project)}")
        for conflict in self.conflicts:
            print(f"CONFLICT {conflict}")

    def apply(self) -> None:
        if self.conflicts:
            raise LifecycleError("Installation has conflicts; no files were changed")
        for change in self.changes:
            if change.action == "DELETE":
                change.path.unlink()
            elif change.content is not None:
                _atomic_write(change.path, change.content)


def _atomic_write(path: Path, content: bytes) -> None:
    _check_directory(path.parent, label="managed parent")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise LifecycleError(f"Unsafe managed output path: {path}")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fchmod(stream.fileno(), 0o644)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def install_plan(root: Path, project: Path, *, with_memory: bool) -> CodexInstallPlan:
    project = _validate_project(project)
    generated = _bundle_agents(root)
    codex_dir = project / ".codex"
    agents_dir = codex_dir / "agents"
    _check_directory(codex_dir, label=".codex")
    _check_directory(agents_dir, label=".codex/agents")
    manifest = _read_manifest(codex_dir)
    managed = manifest["agents"] if manifest else {}
    plan = CodexInstallPlan(project)
    next_agents: dict[str, str] = {}
    for relative, content in generated.items():
        destination = _safe_child(codex_dir, relative)
        if destination.is_symlink() or destination.parent.is_symlink():
            plan.conflicts.append(f"{destination}: symlinked managed path")
            continue
        expected = digest(content)
        next_agents[relative] = expected
        if not destination.exists():
            plan.add("CREATE", destination, content)
        elif not destination.is_file():
            plan.conflicts.append(f"{destination}: not a regular file")
        elif relative not in managed:
            plan.conflicts.append(f"{destination}: user-owned agent would be overwritten")
        else:
            current = destination.read_bytes()
            if digest(current) != managed[relative]:
                plan.conflicts.append(f"{destination}: managed agent was modified; preserving it")
            elif current == content:
                plan.add("SKIP", destination)
            else:
                plan.add("UPDATE", destination, content)
    # A renamed/removed generated agent can be removed only if it still matches
    # the installed hash recorded by the prior manifest.
    for relative, installed_hash in managed.items():
        if relative in generated:
            continue
        destination = _safe_child(codex_dir, relative)
        if destination.is_symlink() or not destination.exists() or not destination.is_file():
            plan.conflicts.append(f"{destination}: stale managed artifact is unsafe or missing")
        elif digest(destination.read_bytes()) != installed_hash:
            plan.conflicts.append(f"{destination}: stale managed artifact was modified")
        else:
            plan.add("DELETE", destination)

    memory_state = manifest.get("memory_mcp") if manifest else None
    next_memory = memory_state
    if with_memory:
        config = codex_dir / "config.toml"
        try:
            content, action = _config_with_block(
                config,
                _mcp_block(root, project),
                owned_hash=memory_state.get("hash") if memory_state else None,
            )
            plan.add(action, config, content)
            block_bounds = _mcp_bounds(content)
            assert block_bounds is not None
            start, end = block_bounds
            next_memory = {"managed": True, "config": "config.toml", "section": MCP_SECTION, "hash": digest(content[start:end])}
        except LifecycleError as exc:
            plan.conflicts.append(str(exc))

    next_manifest = {"version": MANIFEST_VERSION, "agents": next_agents}
    if next_memory:
        next_manifest["memory_mcp"] = next_memory
    manifest_path = codex_dir / MANIFEST
    encoded_manifest = (json.dumps(next_manifest, indent=2, sort_keys=True) + "\n").encode()
    if manifest_path.exists() and manifest_path.is_file() and manifest_path.read_bytes() == encoded_manifest:
        plan.add("SKIP", manifest_path)
    else:
        plan.add("CREATE" if not manifest_path.exists() else "UPDATE", manifest_path, encoded_manifest)
    return plan


def uninstall_plan(project: Path) -> CodexInstallPlan:
    project = _validate_project(project)
    codex_dir = project / ".codex"
    _check_directory(codex_dir, label=".codex", create_ok=False)
    manifest = _read_manifest(codex_dir)
    if manifest is None:
        raise LifecycleError("No toolkit ownership manifest found; refusing to remove user-owned files")
    plan = CodexInstallPlan(project)
    for relative, installed_hash in manifest["agents"].items():
        destination = _safe_child(codex_dir, relative)
        if destination.is_symlink() or not destination.is_file():
            plan.conflicts.append(f"{destination}: managed agent is missing or unsafe")
        elif digest(destination.read_bytes()) != installed_hash:
            plan.conflicts.append(f"{destination}: managed agent was modified; preserving it")
        else:
            plan.add("DELETE", destination)
    memory = manifest.get("memory_mcp")
    if memory and memory.get("managed"):
        config = _safe_child(codex_dir, memory.get("config", ""))
        try:
            plan.add("UPDATE", config, _remove_mcp_block(config, memory.get("hash", "")))
        except LifecycleError as exc:
            plan.conflicts.append(str(exc))
    manifest_path = codex_dir / MANIFEST
    # Do not remove the manifest while any protected artifact remains.
    if not plan.conflicts:
        plan.add("DELETE", manifest_path)
    return plan


def _generated_state(root: Path) -> tuple[str, str]:
    """Check staleness through the existing generator, without repairing it."""
    command = [sys.executable, "-B", str(root / "scripts" / "sync-runtime"), "codex", "--check"]
    try:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "INVALID", str(exc)
    if result.returncode == 0:
        return "OK", ""
    if result.returncode == 1:
        return "DRIFT", "Run: oc sync codex"
    return "INVALID", (result.stderr.strip() or result.stdout.strip() or "sync check failed")


def doctor(root: Path, project: Path, *, verbose: bool) -> int:
    project = _validate_project(project)
    status, detail = _generated_state(root)
    findings: list[tuple[str, str, str]] = [("Generated bundle", status, detail)]
    severity = 0 if status == "OK" else (1 if status == "DRIFT" else 2)
    codex_dir = project / ".codex"
    if codex_dir.is_symlink():
        manifest = None
        findings.append(("Managed manifest", "INVALID", f"Refusing symlinked .codex: {codex_dir}"))
        severity = max(severity, 2)
    elif not codex_dir.exists():
        manifest = None
        findings.append(("Managed manifest", "NOT INSTALLED", ""))
        severity = max(severity, 1)
    else:
        try:
            _check_directory(codex_dir, label=".codex", create_ok=False)
            manifest = _read_manifest(codex_dir)
        except LifecycleError as exc:
            manifest = None
            findings.append(("Managed manifest", "INVALID", str(exc)))
            severity = max(severity, 2)
    if manifest is None and codex_dir.exists() and not any(label == "Managed manifest" for label, _, _ in findings):
        findings.append(("Managed manifest", "MISSING", "not installed by this toolkit"))
        severity = max(severity, 1)
    elif manifest is not None:
        findings.append(("Managed manifest", "OK", ""))
        try:
            expected = _bundle_agents(root) if status != "INVALID" else {}
        except LifecycleError:
            # The generated-state finding above already reports this. Continue
            # inspecting installed state instead of turning a drift report into
            # an exception from a read-only command.
            expected = {}
        agents_ok = 0
        drift: list[str] = []
        for relative, installed_hash in manifest["agents"].items():
            path = _safe_child(codex_dir, relative)
            if path.is_symlink() or not path.is_file():
                drift.append(f"missing {relative}")
            elif digest(path.read_bytes()) != installed_hash:
                drift.append(f"modified {relative}")
            elif relative not in expected:
                drift.append(f"not generated {relative}")
            elif path.read_bytes() != expected[relative]:
                drift.append(f"outdated {relative}")
            else:
                agents_ok += 1
        for relative in expected:
            if relative not in manifest["agents"]:
                drift.append(f"unmanaged generated {relative}")
        findings.append(("Agents installed", f"OK ({agents_ok})" if not drift else "DRIFT", "; ".join(drift)))
        severity = max(severity, 1 if drift else 0)
        memory = manifest.get("memory_mcp")
        if memory and memory.get("managed"):
            try:
                config = _safe_child(codex_dir, memory.get("config", ""))
                if config.is_symlink() or not config.is_file():
                    raise LifecycleError("managed config is missing or unsafe")
                original = config.read_bytes()
                bounds = _mcp_bounds(original)
                valid = bounds is not None and digest(original[bounds[0]:bounds[1]]) == memory.get("hash")
                findings.append(("MCP registration", "OK" if valid else "DRIFT", "" if valid else "managed table missing or modified"))
                severity = max(severity, 0 if valid else 1)
            except (OSError, LifecycleError):
                findings.append(("MCP registration", "DRIFT", "managed config unavailable"))
                severity = max(severity, 1)
        else:
            findings.append(("MCP registration", "NOT MANAGED", "memory is opt-in"))
    plugin = root / "config" / "plugins.json"
    plugin_ok = False
    if plugin.is_file() and not plugin.is_symlink():
        try:
            plugin_config = json.loads(plugin.read_text())
            entry = plugin_config["plugins"]["opencode-memory-plugin"]
            plugin_ok = (
                isinstance(entry.get("repository"), str)
                and isinstance(entry.get("ref"), str)
                and bool(re.fullmatch(r"[0-9a-f]{40}", entry["ref"]))
            )
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            plugin_ok = False
    findings.append(("Memory plugin", "OK" if plugin_ok else "MISSING", "pinned local plugin configuration" if plugin_ok else ""))
    severity = max(severity, 0 if plugin_ok else 1)
    launcher = root / "scripts" / "memory-mcp"
    findings.append(("Memory MCP", "OK" if launcher.is_file() and not launcher.is_symlink() else "MISSING", str(launcher) if verbose else ""))
    severity = max(severity, 0 if launcher.is_file() and not launcher.is_symlink() else 1)
    findings.append(("Node", "OK" if shutil.which("node") else "MISSING", ""))
    severity = max(severity, 0 if shutil.which("node") else 1)
    print("Codex local integration")
    print()
    for label, state, note in findings:
        suffix = f" — {note}" if note and (verbose or state != "OK") else ""
        print(f"{label:<22} {state}{suffix}")
    print(f"Private vault access   NOT CHECKED")
    return severity


def _target(value: str | None) -> Path:
    return Path(value) if value else Path.cwd()


def main(root: Path) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    install = sub.add_parser("install", help="install generated Codex agents into a project")
    install.add_argument("--cwd", help="target project (defaults to current directory)")
    install.add_argument("--dry-run", action="store_true", help="show changes without writing")
    install.add_argument("--with-memory", action="store_true", help="explicitly register the local memory MCP")
    uninstall = sub.add_parser("uninstall", help="remove only toolkit-owned Codex artifacts")
    uninstall.add_argument("--cwd", help="target project (defaults to current directory)")
    uninstall.add_argument("--dry-run", action="store_true", help="show changes without writing")
    check = sub.add_parser("doctor", help="read-only Codex integration check")
    check.add_argument("--cwd", help="target project (defaults to current directory)")
    check.add_argument("--verbose", action="store_true", help="show non-secret diagnostic paths")
    args = parser.parse_args()
    try:
        if args.command == "doctor":
            return doctor(root, _target(args.cwd), verbose=args.verbose)
        if args.command == "install" and args.cwd is None and _validate_project(Path.cwd()) == root.resolve():
            raise LifecycleError("Refusing to install into the toolkit checkout by default; pass --cwd explicitly")
        plan = install_plan(root, _target(args.cwd), with_memory=args.with_memory) if args.command == "install" else uninstall_plan(_target(args.cwd))
        plan.show()
        if plan.conflicts:
            return 2
        if args.dry_run:
            print("No files written (--dry-run).")
            return 0
        plan.apply()
        print("Codex local installation updated." if args.command == "install" else "Toolkit-owned Codex artifacts removed.")
        return 0
    except LifecycleError as exc:
        print(f"Codex lifecycle failed: {exc}", file=sys.stderr)
        return 2
