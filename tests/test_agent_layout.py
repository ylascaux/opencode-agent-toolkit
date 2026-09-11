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


class AgentDirectoryLayoutTests(unittest.TestCase):
    def test_exact_agent_catalog_is_directory_driven(self):
        directories = sorted(
            path for path in AGENTS.iterdir()
            if path.is_dir() and not path.name.startswith("_")
        )
        self.assertEqual(len(directories), 41)
        for directory in directories:
            self.assertTrue((directory / "agent.json").is_file(), directory.name)
            self.assertTrue((directory / "prompt.md").is_file(), directory.name)
            self.assertTrue((directory / "permissions.json").is_file(), directory.name)

    def test_no_legacy_editable_catalogs_remain(self):
        self.assertFalse((AGENTS / "manifest.json").exists())
        self.assertFalse((AGENTS / "permissions").exists())
        self.assertFalse((ROOT / "profiles" / "agent-tiers.json").exists())

    def test_loader_builds_valid_graph_and_model_catalog(self):
        specs = MODULE["load_agents"]()
        children = MODULE["children_by_parent"](specs)
        self.assertEqual(len(specs), 41)
        self.assertEqual(specs["meta-router"].mode, "primary")
        self.assertEqual(specs["builder"].tier, "medium")
        self.assertEqual(specs["mock-generator"].tier, "low")
        self.assertEqual(specs["source-discovery"].tier, "low")
        self.assertEqual(specs["structured-extractor"].tier, "medium")
        self.assertEqual(specs["entity-resolver"].tier, "medium")
        self.assertEqual(specs["research-runner"].tier, "low")
        self.assertEqual(specs["platform-architect"].tier, "high")
        self.assertIn("docs-writer", children["platform-architect"])
        self.assertIn("terraform-terragrunt", children["platform-architect"])
        self.assertIn("source-discovery", children["orchestrator"])
        self.assertIn("structured-extractor", children["orchestrator"])
        self.assertIn("entity-resolver", children["orchestrator"])
        self.assertIn("research-runner", children["meta-router"])
        self.assertIn("source-discovery", children["research-runner"])
        self.assertIn("structured-extractor", children["research-runner"])
        self.assertIn("entity-resolver", children["research-runner"])
        self.assertEqual(children["builder"], [])

    def test_generated_manifest_is_derived_and_points_back_to_source(self):
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], check=True)
        manifest = json.loads((ROOT / ".generated" / "agents.json").read_text())
        self.assertEqual(len(manifest), 41)
        self.assertEqual(manifest["aws-platform"]["source"], "agents/aws-platform")
        self.assertIn("platform-architect", manifest["aws-platform"]["parents"])
        self.assertIn("aws-platform", manifest["platform-architect"]["children"])
        self.assertIn("orchestrator", manifest["source-discovery"]["parents"])
        self.assertIn("research-runner", manifest["source-discovery"]["parents"])

    def test_new_agent_scaffolder_creates_all_three_files(self):
        # Execute a copy of the scaffolder in a minimal temporary toolkit so the
        # real repository is never mutated by the test.
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
                    "platform-architect",
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
            self.assertTrue((target / "prompt.md").exists())
            self.assertTrue((target / "permissions.json").exists())
            config = json.loads((target / "agent.json").read_text())
            self.assertEqual(config["parents"], ["platform-architect"])
            self.assertEqual(config["model_env"], "MODEL_CLOUDFLARE")


if __name__ == "__main__":
    unittest.main()
