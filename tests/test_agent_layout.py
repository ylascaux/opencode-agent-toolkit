import json
import runpy
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"
MODULE = runpy.run_path(str(ROOT / "scripts" / "agent_config.py"), run_name="agent_config_test")

CORE = {
    "meta-router",
    "orchestrator",
    "builder",
    "debugger",
    "tester",
    "reviewer",
    "platform-architect",
    "security-lead",
    "research-runner",
}


class AgentDirectoryLayoutTests(unittest.TestCase):
    def test_active_catalog_is_small_and_explicit(self):
        catalog = json.loads((AGENTS / "catalog.json").read_text())["agents"]
        self.assertEqual(set(catalog), CORE)
        self.assertEqual(len(catalog), 9)
        for name in catalog:
            directory = AGENTS / name
            for filename in ["agent.json", "prompt.md", "permissions.json"]:
                self.assertTrue((directory / filename).is_file(), f"{name}: {filename}")

    def test_loader_uses_only_active_catalog_and_builds_valid_graph(self):
        specs = MODULE["load_agents"]()
        children = MODULE["children_by_parent"](specs)
        self.assertEqual(set(specs), CORE)
        self.assertEqual(specs["meta-router"].mode, "primary")
        self.assertEqual(specs["orchestrator"].tier, "high")
        self.assertEqual(specs["reviewer"].tier, "high")
        self.assertEqual(specs["security-lead"].tier, "high")
        self.assertEqual(specs["platform-architect"].tier, "high")
        self.assertEqual(specs["research-runner"].tier, "medium")
        self.assertEqual(
            set(children["meta-router"]),
            {"orchestrator", "reviewer", "platform-architect", "security-lead", "research-runner"},
        )
        self.assertEqual(
            set(children["orchestrator"]),
            {"builder", "debugger", "tester", "reviewer", "security-lead", "research-runner"},
        )
        self.assertEqual(children["platform-architect"], ["reviewer"])
        for leaf in ["builder", "debugger", "tester", "reviewer", "security-lead", "research-runner"]:
            self.assertEqual(children[leaf], [])

    def test_generated_manifest_contains_only_core_agents(self):
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], check=True)
        manifest = json.loads((ROOT / ".generated" / "agents.json").read_text())
        self.assertEqual(set(manifest), CORE)
        self.assertEqual(manifest["builder"]["source"], "agents/builder")
        self.assertIn("reviewer", manifest["orchestrator"]["children"])
        self.assertIn("reviewer", manifest["platform-architect"]["children"])

    def test_new_agent_scaffolder_does_not_implicitly_activate_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "toolkit"
            scripts = root / "scripts"
            scripts.mkdir(parents=True)
            shutil.copy2(ROOT / "scripts" / "new-agent", scripts / "new-agent")
            result = subprocess.run(
                [
                    "python3",
                    str(scripts / "new-agent"),
                    "cloudflare",
                    "--parent",
                    "orchestrator",
                    "--tier",
                    "medium",
                    "--model-profile",
                    "reasoning",
                ],
                cwd=root,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            target = root / "agents" / "cloudflare"
            self.assertTrue((target / "agent.json").exists())
            config = json.loads((target / "agent.json").read_text())
            self.assertEqual(config["parents"], ["orchestrator"])


if __name__ == "__main__":
    unittest.main()
