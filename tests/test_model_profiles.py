import runpy
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESOLVER = runpy.run_path(str(ROOT / "scripts" / "resolve-models"))
PROFILE = runpy.run_path(str(ROOT / "scripts" / "apply-profile"))


class ModelProfileTests(unittest.TestCase):
    def test_resolver_maps_agents_to_three_tiers(self):
        resolve = RESOLVER["resolve"]
        result = resolve({
            "MODEL_LOW": "test/luna",
            "MODEL_MEDIUM": "test/terra",
            "MODEL_HIGH": "test/sol",
        })
        self.assertEqual(len(result), 37)
        self.assertEqual(result["MODEL_MOCK_GENERATOR"], "test/luna")
        self.assertEqual(result["MODEL_SECRETS"], "test/luna")
        self.assertEqual(result["MODEL_DOCS"], "test/terra")
        self.assertEqual(result["MODEL_PROJECT_SCANNER"], "test/terra")
        self.assertEqual(result["MODEL_EVIDENCE_AUDITOR"], "test/terra")
        self.assertEqual(result["MODEL_BUILDER"], "test/terra")
        self.assertEqual(result["MODEL_PLATFORM_ARCHITECT"], "test/sol")
        self.assertEqual(result["MODEL_APPSEC"], "test/sol")

    def test_default_quality_policy_keeps_only_bounded_agents_low(self):
        tiers = RESOLVER["load_tiers"]()
        low_agents = {name for name, tier in tiers.items() if tier == "low"}
        self.assertEqual(low_agents, {"MODEL_MOCK_GENERATOR", "MODEL_SECRETS"})

    def test_architecture_evidence_sources_are_not_low(self):
        tiers = RESOLVER["load_tiers"]()
        for variable in [
            "MODEL_PROJECT_SCANNER",
            "MODEL_DOCS",
            "MODEL_OBSERVABILITY",
            "MODEL_FINOPS",
            "MODEL_EVIDENCE_AUDITOR",
            "MODEL_BRAINSTORM",
        ]:
            self.assertIn(tiers[variable], {"medium", "high"}, variable)

    def test_per_agent_override_wins_over_tier(self):
        resolve = RESOLVER["resolve"]
        result = resolve({
            "MODEL_LOW": "test/luna",
            "MODEL_MEDIUM": "test/terra",
            "MODEL_HIGH": "test/sol",
            "MODEL_BUILDER": "personal/codex",
        })
        self.assertEqual(result["MODEL_BUILDER"], "personal/codex")
        self.assertEqual(result["MODEL_TESTER"], "test/terra")

    def test_default_copilot_profile_is_luna_terra_sol(self):
        values = PROFILE["load_profile"]("copilot")
        self.assertEqual(values["MODEL_LOW"], "github-copilot/gpt-5.6-luna")
        self.assertEqual(values["MODEL_MEDIUM"], "github-copilot/gpt-5.6-terra")
        self.assertEqual(values["MODEL_HIGH"], "github-copilot/gpt-5.6-sol")

    def test_codex_profile_is_luna_terra_astra(self):
        values = PROFILE["load_profile"]("codex")
        self.assertEqual(values["MODEL_PROFILE"], "codex")
        self.assertEqual(values["MODEL_LOW"], "openai/gpt-5.6-luna")
        self.assertEqual(values["MODEL_MEDIUM"], "openai/gpt-5.6-terra")
        self.assertEqual(values["MODEL_HIGH"], "openai/gpt-6-astra")

    def test_profile_switch_backs_up_and_removes_generated_agent_mappings(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env_file = tmp_path / ".env"
            backup_file = tmp_path / ".env.model-overrides.backup"
            env_file.write_text(
                "OPENCODE_MAJOR=1\n"
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
            self.assertIn("MODEL_LOW=github-copilot/gpt-5.6-luna", text)
            self.assertNotIn("MODEL_BUILDER=", text)
            self.assertIn("PROJECTS_ROOT=$HOME/Projects", text)
            self.assertTrue(backup_file.exists())
            self.assertIn("MODEL_BUILDER=old/generated", backup_file.read_text())


if __name__ == "__main__":
    unittest.main()
