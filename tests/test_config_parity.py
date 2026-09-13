import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = ROOT / "agents"
OPEN_CODE_GOLDEN = ROOT / "tests" / "fixtures" / "opencode-output.sha256.json"

LEADS = {"meta-router", "orchestrator", "review-lead", "platform-architect", "security-lead", "research-runner"}
RESTRICTED_RESEARCH_AGENTS = {"research-runner"}
EXPECTED_META_CHILDREN = {
    "orchestrator", "review-lead", "platform-architect", "security-lead",
    "arbiter", "deep-reasoner", "evidence-auditor", "research-runner",
}
WRITERS = {
    "builder", "tester", "mock-generator", "debugger", "python-specialist",
    "go-specialist", "cicd", "docs-writer", "terraform-terragrunt",
}
APPROVAL_SENSITIVE_PATTERNS = {
    "*.env", "*.env.*", "**/.env", "**/.env.*", "*.pem", "*.key",
}
DENIED_HOST_CREDENTIAL_PATTERNS = {
    "*id_rsa*", "*id_ed25519*", "**/.ssh/**", "**/.aws/**", "**/.kube/**",
    "**/.azure/**", "**/.config/gcloud/**", "**/.config/gh/**",
}
READ_ONLY_GIT = {
    "git status*", "git diff*", "git show*", "git log*", "git rev-parse*",
    "git rev-list*", "git ls-files*", "git ls-tree*", "git grep*", "git blame*",
}


def last_v2_effect(agent: dict, action: str, resource: str) -> str | None:
    effect = None
    for rule in agent["permissions"]:
        if rule.get("action") != action:
            continue
        if rule.get("resource") in {"*", resource}:
            effect = rule.get("effect")
    return effect


def source_agent_dirs() -> list[Path]:
    return sorted(
        path for path in AGENTS_DIR.iterdir()
        if path.is_dir() and not path.name.startswith("_")
    )


def generated_artifact_snapshot(root: Path) -> dict[str, bytes | None]:
    snapshot = {}
    for filename in ["opencode.jsonc", "opencode.v2.jsonc"]:
        path = root / filename
        snapshot[filename] = path.read_bytes() if path.is_file() else None

    generated_dir = root / ".generated"
    snapshot[".generated/"] = b"" if generated_dir.is_dir() else None
    if generated_dir.is_dir():
        for path in generated_dir.rglob("*"):
            relative = str(path.relative_to(root))
            snapshot[f"{relative}/" if path.is_dir() else relative] = b"" if path.is_dir() else path.read_bytes()
    return snapshot


def generated_output_digests(root: Path) -> dict[str, str]:
    """Digest deterministic OpenCode artifacts while ignoring fixture root paths."""
    root_marker = str(root.resolve()).encode()

    def digest_file(path: Path) -> str:
        return hashlib.sha256(path.read_bytes().replace(root_marker, b"<ROOT>")).hexdigest()

    def digest_directory(path: Path) -> str:
        digest = hashlib.sha256()
        for artifact in sorted(path.glob("*.md")):
            digest.update(str(artifact.relative_to(root)).encode())
            digest.update(b"\0")
            digest.update(artifact.read_bytes().replace(root_marker, b"<ROOT>"))
            digest.update(b"\0")
        return digest.hexdigest()

    return {
        "opencode.jsonc": digest_file(root / "opencode.jsonc"),
        "opencode.v2.jsonc": digest_file(root / "opencode.v2.jsonc"),
        ".generated/agents.json": digest_file(root / ".generated" / "agents.json"),
        ".generated/prompts": digest_directory(root / ".generated" / "prompts"),
        ".generated/prompts-v1": digest_directory(root / ".generated" / "prompts-v1"),
    }


class GeneratedArtifactSnapshotTests(unittest.TestCase):
    def test_missing_artifacts_are_snapshotted_and_changes_are_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            absent = generated_artifact_snapshot(root)
            self.assertEqual(absent["opencode.jsonc"], None)
            self.assertEqual(absent["opencode.v2.jsonc"], None)
            self.assertEqual(absent[".generated/"], None)

            config = root / "opencode.jsonc"
            config.write_bytes(b"first")
            generated = root / ".generated"
            generated.mkdir()
            generated_file = generated / "prompt.md"
            generated_file.write_bytes(b"prompt")
            populated = generated_artifact_snapshot(root)
            self.assertNotEqual(absent, populated)

            config.write_bytes(b"second")
            self.assertNotEqual(populated, generated_artifact_snapshot(root))
            config.write_bytes(b"first")
            generated_file.unlink()
            self.assertNotEqual(populated, generated_artifact_snapshot(root))


class ConfigPolicyTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        repository_artifacts = generated_artifact_snapshot(ROOT)
        cls.fixture = tempfile.TemporaryDirectory()
        cls.fixture_root = Path(cls.fixture.name)
        shutil.copytree(AGENTS_DIR, cls.fixture_root / "agents")
        shutil.copytree(ROOT / "skills", cls.fixture_root / "skills")
        fixture_scripts = cls.fixture_root / "scripts"
        fixture_scripts.mkdir()
        for filename in ["generate-config", "agent_config.py", "apply-reliability"]:
            shutil.copy2(ROOT / "scripts" / filename, fixture_scripts / filename)
        shutil.copytree(ROOT / "runtime" / "common", cls.fixture_root / "runtime" / "common")
        shutil.copytree(ROOT / "runtime" / "opencode", cls.fixture_root / "runtime" / "opencode")
        shutil.copy2(ROOT / "reliability.json", cls.fixture_root / "reliability.json")

        subprocess.run(
            ["python3", str(fixture_scripts / "generate-config")],
            check=True,
            capture_output=True,
            text=True,
            cwd=cls.fixture_root,
        )
        subprocess.run(
            ["python3", str(fixture_scripts / "apply-reliability")],
            check=True,
            capture_output=True,
            text=True,
            cwd=cls.fixture_root,
        )
        if repository_artifacts != generated_artifact_snapshot(ROOT):
            raise AssertionError("parity fixture generation must not modify repository output artifacts")
        cls.v1 = json.loads((cls.fixture_root / "opencode.jsonc").read_text())
        cls.v2 = json.loads((cls.fixture_root / "opencode.v2.jsonc").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()

    def test_agent_sets_match_and_count(self):
        self.assertEqual(set(self.v1["agent"]), set(self.v2["agents"]))
        self.assertEqual(len(self.v1["agent"]), 41)
        self.assertEqual({path.name for path in source_agent_dirs()}, set(self.v1["agent"]))

    def test_open_code_artifacts_match_the_pre_normalization_golden_snapshot(self):
        expected = json.loads(OPEN_CODE_GOLDEN.read_text())
        self.assertEqual(generated_output_digests(self.fixture_root), expected)

    def test_every_agent_is_self_contained(self):
        for directory in source_agent_dirs():
            for filename in ["agent.json", "prompt.md", "permissions.json"]:
                self.assertTrue((directory / filename).exists(), f"{directory.name}: {filename}")
            config = json.loads((directory / "agent.json").read_text())
            self.assertIn("description", config, directory.name)
            self.assertIn("model_env", config, directory.name)
            self.assertIn("tier", config, directory.name)
            self.assertIn("parents", config, directory.name)
            self.assertIn("## Operating method", (directory / "prompt.md").read_text(), directory.name)
            self.assertIn("## Non-negotiables", (directory / "prompt.md").read_text(), directory.name)

    def test_defaults_are_centralized(self):
        defaults = AGENTS_DIR / "_defaults"
        self.assertTrue((defaults / "agent.json").is_file())
        self.assertTrue((defaults / "prompt.md").is_file())
        self.assertTrue((defaults / "permissions.json").is_file())

    def test_every_model_env_has_a_tier_in_its_agent_json(self):
        for directory in source_agent_dirs():
            config = json.loads((directory / "agent.json").read_text())
            self.assertRegex(config["model_env"], r"^MODEL_[A-Z0-9_]+$")
            self.assertIn(config["tier"], {"low", "medium", "high"})

    def test_default_env_defines_three_tiers(self):
        env = (ROOT / ".env.example").read_text()
        for name in ["MODEL_LOW", "MODEL_MEDIUM", "MODEL_HIGH"]:
            self.assertRegex(env, rf"(?m)^{name}=.+$")

    def test_meta_router_is_default(self):
        self.assertEqual(self.v1["default_agent"], "meta-router")
        self.assertEqual(self.v2["default_agent"], "meta-router")

    def test_command_sets_match(self):
        self.assertEqual(set(self.v1["command"]), set(self.v2["commands"]))

    def test_meta_router_catalog_is_small_and_hierarchical(self):
        self.assertEqual(set(self.v1["agent"]["meta-router"]["permission"]["task"]), {"*", *EXPECTED_META_CHILDREN})
        self.assertEqual(set(self.v2["agents"]["meta-router"]["permissions"][0].keys()), {"action", "resource", "effect"})
        for child in EXPECTED_META_CHILDREN:
            self.assertEqual(last_v2_effect(self.v2["agents"]["meta-router"], "subagent", child), "allow")

    def test_leaf_agents_cannot_delegate_unattended(self):
        for name in self.v1["agent"]:
            if name in LEADS:
                continue
            self.assertEqual(self.v1["agent"][name]["permission"]["task"]["*"], "deny", name)
            self.assertEqual(last_v2_effect(self.v2["agents"][name], "subagent", "*"), "deny", name)

    def test_nested_subagents_stay_bounded(self):
        self.assertEqual(self.v1["subagent_depth"], 2)
        self.assertEqual(self.v2["experimental"]["subagent_depth"], 2)

    def test_edit_is_allow_for_writers_and_ask_for_everyone_else(self):
        for name in self.v1["agent"]:
            expected = "allow" if name in WRITERS else "ask"
            self.assertEqual(self.v1["agent"][name]["permission"]["edit"], expected, name)
            self.assertEqual(last_v2_effect(self.v2["agents"][name], "edit", "*"), expected, name)

    def test_non_destructive_shell_defaults_to_ask_and_safe_git_is_allowed(self):
        for name, agent in self.v1["agent"].items():
            self.assertEqual(agent["permission"]["bash"]["*"], "ask", name)
            for pattern in READ_ONLY_GIT:
                self.assertEqual(agent["permission"]["bash"][pattern], "allow", f"{name}: {pattern}")

    def test_destructive_commands_stay_denied(self):
        for name, agent in self.v1["agent"].items():
            shell = agent["permission"]["bash"]
            for pattern in ["git reset --hard*", "git clean -f*", "git push --force*", "terraform destroy*", "kubectl delete*", "helm uninstall*", "rm -rf*"]:
                self.assertEqual(shell[pattern], "deny", f"{name}: {pattern}")

    def test_sensitive_reads_are_approved_or_denied_by_scope(self):
        for name, agent in self.v1["agent"].items():
            read = agent["permission"]["read"]
            for pattern in APPROVAL_SENSITIVE_PATTERNS:
                self.assertEqual(read[pattern], "ask", f"{name}: {pattern}")
            for pattern in DENIED_HOST_CREDENTIAL_PATTERNS:
                self.assertEqual(read[pattern], "deny", f"{name}: {pattern}")

    def test_every_agent_has_open_web_and_prompted_skill_policy(self):
        for name, agent in self.v1["agent"].items():
            self.assertEqual(agent["permission"]["webfetch"], "allow", name)
            self.assertEqual(agent["permission"]["websearch"], "allow", name)
            self.assertEqual(agent["permission"]["skill"], "ask", name)

    def test_project_scanner_can_read_projects_without_prompt(self):
        self.assertEqual(self.v1["agent"]["project-scanner"]["permission"]["read"]["*"], "allow")
        self.assertEqual(last_v2_effect(self.v2["agents"]["project-scanner"], "read", "*"), "allow")

    def test_platform_architect_can_delegate_durable_document_writing(self):
        self.assertEqual(self.v1["agent"]["platform-architect"]["permission"]["task"]["docs-writer"], "allow")
        self.assertEqual(last_v2_effect(self.v2["agents"]["platform-architect"], "subagent", "docs-writer"), "allow")

    def test_review_lead_can_independently_recheck_architecture_evidence(self):
        for child in ["platform-review", "project-scanner"]:
            self.assertEqual(self.v1["agent"]["review-lead"]["permission"]["task"][child], "allow")
            self.assertEqual(last_v2_effect(self.v2["agents"]["review-lead"], "subagent", child), "allow")

    def test_architecture_command_requires_independent_post_design_review(self):
        architecture = self.v2["commands"]["architecture"]["template"]
        self.assertIn("review-lead", architecture)
        self.assertIn("independently", architecture)
        self.assertIn("docs-writer", architecture)

    def test_architecture_review_command_is_independent(self):
        architecture_review = self.v2["commands"]["architecture-review"]["template"]
        self.assertIn("review-lead", architecture_review)
        self.assertIn("Independently", architecture_review)
