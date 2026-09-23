import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.common.normalization import load_normalized_agents, load_normalized_skills
from runtime.opencode.adapter import OpenCodeAdapter

ROOT = Path(__file__).resolve().parents[1]


class OpenCodeAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.specs = load_normalized_agents()
        cls.skills = load_normalized_skills()
        cls.adapter = OpenCodeAdapter()

    def test_normalized_agents_build_stable_runtime_shape(self):
        config = self.adapter.build(self.specs)
        self.assertEqual(self.adapter.name, "opencode")
        self.assertEqual(set(config["agents"]), set(self.specs))
        self.assertIn("permissions", config["agents"]["builder"])
        self.assertNotIn("agent", config)
        self.assertNotIn("permission", config["agents"]["builder"])

    def test_delegation_uses_stable_subagent_permissions(self):
        config = self.adapter.build(self.specs)
        rules = [r for r in config["agents"]["meta-router"]["permissions"] if r["action"] == "subagent"]
        self.assertIn({"action": "subagent", "resource": "orchestrator", "effect": "allow"}, rules)

    def test_only_opencode_extension_is_rendered(self):
        builder = replace(
            self.specs["builder"],
            extensions={"opencode": {"custom_open_code_setting": True}, "future-runtime": {"must_not_leak": True}},
        )
        rendered = self.adapter.build({**self.specs, "builder": builder})["agents"]["builder"]
        self.assertTrue(rendered["custom_open_code_setting"])
        self.assertNotIn("must_not_leak", rendered)

    def test_generation_is_deterministic_and_single_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "agents", root / "agents")
            adapter = OpenCodeAdapter(root)
            first_paths = adapter.generate(self.specs, self.skills)
            first = {path.relative_to(root): path.read_bytes() for path in first_paths}
            second_paths = adapter.generate(self.specs, self.skills)
            second = {path.relative_to(root): path.read_bytes() for path in second_paths}
            self.assertEqual(first, second)
            self.assertEqual(first_paths, (root / "opencode.jsonc",))
            self.assertFalse((root / "opencode.v2.jsonc").exists())
            for name, skill in self.skills.items():
                rendered = (root / ".opencode" / "skills" / name / "SKILL.md").read_text()
                self.assertIn(f"name: {name}", rendered)
                self.assertIn(skill.prompt, rendered)


if __name__ == "__main__":
    unittest.main()
