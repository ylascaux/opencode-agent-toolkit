import runpy
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESOLVER = runpy.run_path(str(ROOT / "scripts" / "resolve-models"))
PROFILE = runpy.run_path(str(ROOT / "scripts" / "apply-profile"))


class ModelProfileTests(unittest.TestCase):
    def test_resolver_maps_core_agents_to_three_tiers(self):
        resolve = RESOLVER["resolve"]
        result = resolve({
            "MODEL_LOW": "test/luna-low",
            "MODEL_MEDIUM": "test/luna",
            "MODEL_HIGH": "test/sol",
        })
        self.assertEqual(len(result), 9)
        for key in [
            "MODEL_META_ROUTER", "MODEL_BUILDER", "MODEL_DEBUGGER",
            "MODEL_TESTER", "MODEL_RESEARCH_RUNNER",
        ]:
            self.assertEqual(result[key], "test/luna", key)
        for key in [
            "MODEL_ORCHESTRATOR", "MODEL_REVIEWER",
            "MODEL_PLATFORM_ARCHITECT", "MODEL_SECURITY_LEAD",
        ]:
            self.assertEqual(result[key], "test/sol", key)

    def test_default_quality_policy_has_no_low_core_agents(self):
        tiers = RESOLVER["load_tiers"]()
        self.assertEqual(len(tiers), 9)
        self.assertNotIn("low", set(tiers.values()))
        self.assertEqual(tiers["MODEL_ORCHESTRATOR"], "high")
        self.assertEqual(tiers["MODEL_REVIEWER"], "high")
        self.assertEqual(tiers["MODEL_SECURITY_LEAD"], "high")
        self.assertEqual(tiers["MODEL_PLATFORM_ARCHITECT"], "high")

    def test_apply_profile_replaces_generated_overrides_with_tiers(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env_file = tmp_path / ".env"
            backup_file = tmp_path / ".env.model-overrides.backup"
            env_file.write_text(
                "OPENCODE_MAJOR=2\n"
                "MODEL_PROFILE=old\n"
                "MODEL_LOW=old/low\n"
                "MODEL_MEDIUM=old/medium\n"
                "MODEL_HIGH=old/high\n"
                "MODEL_BUILDER=old/generated\n"
                "PROJECTS_ROOT=$HOME/Projects\n"
            )
            globals_dict = PROFILE["apply_profile"].__globals__
            original_env = globals_dict["ENV_FILE"]
            original_backup = globals_dict["BACKUP_FILE"]
            try:
                globals_dict["ENV_FILE"] = env_file
                globals_dict["BACKUP_FILE"] = backup_file
                PROFILE["apply_profile"]("copilot")
            finally:
                globals_dict["ENV_FILE"] = original_env
                globals_dict["BACKUP_FILE"] = original_backup

            text = env_file.read_text()
            self.assertIn("MODEL_PROFILE=copilot", text)
            self.assertIn("MODEL_LOW=github-copilot/gpt-6-luna", text)
            self.assertIn("MODEL_MEDIUM=github-copilot/gpt-6-luna", text)
            self.assertIn("MODEL_HIGH=github-copilot/gpt-6-sol", text)
            self.assertNotIn("MODEL_BUILDER=", text)
            self.assertIn("PROJECTS_ROOT=$HOME/Projects", text)
            self.assertTrue(backup_file.exists())


if __name__ == "__main__":
    unittest.main()
