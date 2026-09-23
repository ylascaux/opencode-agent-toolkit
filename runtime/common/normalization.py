"""Runtime-neutral agent discovery, normalization, and graph validation."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = ROOT / "agents"
DEFAULTS_DIR = AGENTS_DIR / "_defaults"
SKILLS_DIR = ROOT / "skills"

VALID_MODES = {"primary", "all", "subagent"}
VALID_TIERS = {"low", "medium", "high"}
VALID_MODEL_PROFILES = {"fast", "general", "coding", "reasoning", "deep", "review", "security"}
VALID_PERMISSION_EFFECTS = {"allow", "ask", "deny"}
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

RESERVED_AGENT_KEYS = {
    "description",
    "mode",
    "model_env",
    "tier",
    "model_profile",
    "steps",
    "parents",
    "opencode",
    "codex",
}


@dataclass(frozen=True)
class NormalizedAgent:
    """Resolved canonical agent intent before any runtime renders it."""

    name: str
    path: Path
    description: str
    mode: str
    model_env: str
    tier: str
    model_profile: str
    steps: int
    parents: tuple[str, ...]
    prompt: str
    permissions: dict[str, Any]
    extensions: dict[str, dict[str, Any]]
    default_prompt: str = ""

    @property
    def opencode(self) -> dict[str, Any]:
        """Compatibility accessor for the existing OpenCode renderer."""
        return self.extensions["opencode"]


@dataclass(frozen=True)
class NormalizedSkill:
    """Runtime-neutral reusable instruction set before adapter rendering."""

    name: str
    path: Path
    description: str
    prompt: str
    tags: tuple[str, ...]


def deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_json(path: Path, *, required: bool = True) -> dict:
    if not path.exists():
        if required:
            raise SystemExit(f"Missing agent configuration file: {path.relative_to(ROOT)}")
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Expected a JSON object in {path.relative_to(ROOT)}")
    return data


def validate_permission_tree(value: Any, *, path: str) -> None:
    if isinstance(value, str):
        if value not in VALID_PERMISSION_EFFECTS:
            raise SystemExit(f"Invalid permission effect at {path}: {value!r}")
        return
    if isinstance(value, dict):
        for key, child in value.items():
            validate_permission_tree(child, path=f"{path}.{key}")
        return
    raise SystemExit(f"Permission values must be allow/ask/deny or objects at {path}")


def discover_agent_dirs() -> list[Path]:
    if not DEFAULTS_DIR.is_dir():
        raise SystemExit("Missing agents/_defaults directory")
    catalog = load_json(CATALOG_PATH)
    names = catalog.get("agents")
    if (
        not isinstance(names, list)
        or not names
        or not all(isinstance(name, str) and NAME_RE.fullmatch(name) for name in names)
    ):
        raise SystemExit("agents/catalog.json must contain a non-empty 'agents' array of valid names")
    if len(set(names)) != len(names):
        raise SystemExit("agents/catalog.json contains duplicate agent names")

    directories = []
    for name in names:
        path = AGENTS_DIR / name
        if not path.is_dir():
            raise SystemExit(f"Catalog agent directory is missing: agents/{name}")
        directories.append(path)
    return directories


def _resolved_config(name: str, directory: Path, defaults: dict) -> dict:
    local = load_json(directory / "agent.json")
    unknown = set(local) - RESERVED_AGENT_KEYS
    if unknown:
        raise SystemExit(f"Unknown agent.json key(s) for {name}: {', '.join(sorted(unknown))}")
    config = deep_merge(defaults, local)
    config.setdefault("model_env", "MODEL_" + name.upper().replace("-", "_"))
    return config


def _validate_agent(name: str, directory: Path, config: dict) -> None:
    if not NAME_RE.fullmatch(name):
        raise SystemExit(f"Invalid agent directory name: {name!r}")
    description = config.get("description")
    if not isinstance(description, str) or not description.strip():
        raise SystemExit(f"{name}: description must be a non-empty string")
    mode = config.get("mode")
    if mode not in VALID_MODES:
        raise SystemExit(f"{name}: mode must be one of {sorted(VALID_MODES)}")
    model_env = config.get("model_env")
    if not isinstance(model_env, str) or not re.fullmatch(r"MODEL_[A-Z0-9_]+", model_env):
        raise SystemExit(f"{name}: model_env must look like MODEL_FOO")
    tier = config.get("tier")
    if tier not in VALID_TIERS:
        raise SystemExit(f"{name}: tier must be one of {sorted(VALID_TIERS)}")
    model_profile = config.get("model_profile")
    if model_profile not in VALID_MODEL_PROFILES:
        raise SystemExit(f"{name}: model_profile must be one of {sorted(VALID_MODEL_PROFILES)}")
    steps = config.get("steps")
    if not isinstance(steps, int) or isinstance(steps, bool) or steps < 1:
        raise SystemExit(f"{name}: steps must be a positive integer")
    parents = config.get("parents")
    if not isinstance(parents, list) or not all(isinstance(parent, str) for parent in parents):
        raise SystemExit(f"{name}: parents must be an array of agent names")
    if len(set(parents)) != len(parents):
        raise SystemExit(f"{name}: parents contains duplicates")
    opencode = config.get("opencode")
    if not isinstance(opencode, dict):
        raise SystemExit(f"{name}: opencode must be an object")
    if "codex" in config and not isinstance(config["codex"], dict):
        raise SystemExit(f"{name}: codex must be an object")
    prompt_path = directory / "prompt.md"
    if not prompt_path.exists():
        raise SystemExit(f"Missing agent prompt: {prompt_path.relative_to(ROOT)}")
    permissions_path = directory / "permissions.json"
    if not permissions_path.exists():
        raise SystemExit(f"Missing agent permissions: {permissions_path.relative_to(ROOT)}")


def _children_by_parent(specs: dict[str, NormalizedAgent]) -> dict[str, list[str]]:
    children = {name: [] for name in specs}
    for child, spec in specs.items():
        for parent in spec.parents:
            if parent not in specs:
                raise SystemExit(f"{child}: unknown parent agent {parent!r}")
            if parent == child:
                raise SystemExit(f"{child}: an agent cannot be its own parent")
            children[parent].append(child)
    return children


def _validate_graph(specs: dict[str, NormalizedAgent]) -> None:
    primary = [name for name, spec in specs.items() if spec.mode == "primary"]
    if len(primary) != 1:
        raise SystemExit(f"Expected exactly one primary agent, found: {primary}")
    root = primary[0]
    if specs[root].parents:
        raise SystemExit(f"Primary agent {root} cannot have parents")

    children = _children_by_parent(specs)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visiting:
            raise SystemExit(f"Delegation cycle detected at {name}")
        if name in visited:
            return
        visiting.add(name)
        for child in children[name]:
            visit(child)
        visiting.remove(name)
        visited.add(name)

    for name in specs:
        visit(name)

    reachable: set[str] = set()
    max_depth: dict[str, int] = {}

    def walk(name: str, depth: int) -> None:
        reachable.add(name)
        max_depth[name] = max(depth, max_depth.get(name, depth))
        if depth > 2:
            raise SystemExit(f"Delegation depth exceeds 2 on path ending at {name} (depth={depth})")
        for child in children[name]:
            walk(child, depth + 1)

    walk(root, 0)
    unreachable = sorted(set(specs) - reachable)
    if unreachable:
        raise SystemExit(
            "Agents are not reachable from the primary routing graph: "
            + ", ".join(unreachable)
            + ". Add a parent in each agent.json."
        )


def load_normalized_agents() -> dict[str, NormalizedAgent]:
    """Load the canonical agent catalog without rendering a runtime artifact."""
    defaults = load_json(DEFAULTS_DIR / "agent.json")
    default_prompt = (DEFAULTS_DIR / "prompt.md").read_text().strip()
    default_permissions = load_json(DEFAULTS_DIR / "permissions.json")
    validate_permission_tree(default_permissions, path="agents/_defaults/permissions.json")

    specs: dict[str, NormalizedAgent] = {}
    model_env_owners: dict[str, str] = {}
    for directory in discover_agent_dirs():
        name = directory.name
        config = _resolved_config(name, directory, defaults)
        _validate_agent(name, directory, config)

        local_permissions = load_json(directory / "permissions.json")
        validate_permission_tree(local_permissions, path=f"agents/{name}/permissions.json")
        if "task" in local_permissions:
            raise SystemExit(
                f"{name}: task/subagent topology belongs in agent.json parents, not permissions.json"
            )
        permissions = deep_merge(default_permissions, local_permissions)

        model_env = config["model_env"]
        other = model_env_owners.get(model_env)
        if other:
            raise SystemExit(f"{name}: model_env {model_env} is already used by {other}")
        model_env_owners[model_env] = name

        specs[name] = NormalizedAgent(
            name=name,
            path=directory,
            description=config["description"].strip(),
            mode=config["mode"],
            model_env=model_env,
            tier=config["tier"],
            model_profile=config["model_profile"],
            steps=config["steps"],
            parents=tuple(config["parents"]),
            prompt=(directory / "prompt.md").read_text().strip(),
            permissions=permissions,
            extensions={
                namespace: copy.deepcopy(config[namespace])
                for namespace in ("opencode", "codex") if namespace in config
            },
            default_prompt=default_prompt,
        )

    _validate_graph(specs)
    return specs


def _skill_error(directory: Path, message: str) -> SystemExit:
    try:
        location = directory.relative_to(ROOT)
    except ValueError:
        location = directory
    return SystemExit(f"{location}: {message}")


def is_valid_skill_name(value: object) -> bool:
    return isinstance(value, str) and len(value) <= 64 and bool(SKILL_NAME_RE.fullmatch(value))


def load_normalized_skills() -> dict[str, NormalizedSkill]:
    """Load one safe, deterministic portable skill catalog from ``skills/``."""
    if SKILLS_DIR.is_symlink() or not SKILLS_DIR.is_dir():
        raise SystemExit("Missing or unsafe skills directory: skills/")

    specs: dict[str, NormalizedSkill] = {}
    metadata_owners: dict[str, Path] = {}
    for directory in sorted(SKILLS_DIR.iterdir(), key=lambda path: path.name):
        if directory.is_symlink():
            raise _skill_error(directory, "refusing symlinked canonical skill directory")
        if not directory.is_dir():
            raise _skill_error(directory, "expected a skill directory")
        if not is_valid_skill_name(directory.name):
            raise _skill_error(directory, "invalid skill directory name")
        metadata_path = directory / "skill.json"
        prompt_path = directory / "SKILL.md"
        if metadata_path.is_symlink() or prompt_path.is_symlink():
            raise _skill_error(directory, "refusing symlinked canonical skill file")
        if not metadata_path.is_file() or not prompt_path.is_file():
            raise _skill_error(directory, "requires regular skill.json and SKILL.md files")
        try:
            metadata = json.loads(metadata_path.read_text())
        except json.JSONDecodeError as exc:
            raise _skill_error(directory, f"invalid JSON in skill.json: {exc}") from exc
        if not isinstance(metadata, dict):
            raise _skill_error(directory, "skill.json must contain an object")
        unknown = set(metadata) - {"name", "description", "tags"}
        if unknown:
            raise _skill_error(directory, f"unknown skill.json key(s): {', '.join(sorted(unknown))}")
        name = metadata.get("name")
        description = metadata.get("description")
        tags = metadata.get("tags", [])
        if not is_valid_skill_name(name):
            raise _skill_error(directory, "name must be a portable skill name")
        if name in metadata_owners:
            raise _skill_error(directory, f"duplicate skill name: {name}")
        metadata_owners[name] = directory
        if name != directory.name:
            raise _skill_error(directory, "name must match its directory")
        if (
            not isinstance(description, str)
            or not description.strip()
            or len(description.strip()) > 1024
            or any(ord(char) < 32 for char in description)
        ):
            raise _skill_error(directory, "description must be a non-empty string up to 1024 characters")
        if not isinstance(tags, list) or not all(isinstance(tag, str) and tag.strip() for tag in tags):
            raise _skill_error(directory, "tags must be an array of non-empty strings")
        normalized_tags = tuple(sorted({tag.strip() for tag in tags}))
        if len(normalized_tags) != len(tags):
            raise _skill_error(directory, "tags must not contain duplicates")
        prompt = prompt_path.read_text().strip()
        if not prompt:
            raise _skill_error(directory, "SKILL.md must not be empty")
        specs[name] = NormalizedSkill(
            name=name,
            path=directory,
            description=description.strip(),
            prompt=prompt,
            tags=normalized_tags,
        )
    if not specs:
        raise SystemExit("No skills found under skills/<name>/")
    return specs


def children_by_parent(specs: dict[str, NormalizedAgent]) -> dict[str, list[str]]:
    children = _children_by_parent(specs)
    for values in children.values():
        values.sort()
    return children


def model_tiers(specs: dict[str, NormalizedAgent] | None = None) -> dict[str, str]:
    specs = specs or load_normalized_agents()
    return {spec.model_env: spec.tier for spec in specs.values()}


def model_profiles(specs: dict[str, NormalizedAgent] | None = None) -> dict[str, str]:
    specs = specs or load_normalized_agents()
    return {spec.model_env: spec.model_profile for spec in specs.values()}
