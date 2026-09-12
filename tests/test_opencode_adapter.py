import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.common.normalization import load_normalized_agents
from runtime.opencode.adapter import OpenCodeAdapter

ROOT = Path(__file__).resolve().parents[1]


class OpenCodeAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.specs = load_normalized_agents()
        cls.adapter = OpenCodeAdapter()

    def test_normalized_agents_build_both_opencode_runtime_shapes(self):
        v1 = self.adapter.build(self.specs, v2=False)
        v2 = self.adapter.build(self.specs, v2=True)

        self.assertEqual(self.adapter.name, "opencode")
        self.assertEqual(set(v1["agent"]), set(self.specs))
        self.assertEqual(set(v2["agents"]), set(self.specs))
        self.assertIn("permission", v1["agent"]["builder"])
        self.assertIn("permissions", v2["agents"]["builder"])

    def test_delegation_is_derived_from_the_normalized_parent_graph(self):
        v1 = self.adapter.build(self.specs, v2=False)
        v2 = self.adapter.build(self.specs, v2=True)

        self.assertEqual(v1["agent"]["builder"]["permission"]["task"], {"*": "deny"})
        self.assertEqual(
            v1["agent"]["meta-router"]["permission"]["task"]["orchestrator"], "allow"
        )
        subagent_rules = [
            rule for rule in v2["agents"]["builder"]["permissions"]
            if rule["action"] == "subagent"
        ]
        self.assertEqual(subagent_rules, [{"action": "subagent", "resource": "*", "effect": "deny"}])

    def test_only_the_opencode_extension_is_rendered(self):
        builder = replace(
            self.specs["builder"],
            extensions={
                "opencode": {"custom_open_code_setting": True},
                "future-runtime": {"must_not_leak": True},
            },
        )
        specs = {**self.specs, "builder": builder}

        rendered = self.adapter.build(specs, v2=False)["agent"]["builder"]
        self.assertTrue(rendered["custom_open_code_setting"])
        self.assertNotIn("must_not_leak", rendered)

    def test_generation_is_deterministic_and_does_not_create_codex_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "agents", root / "agents")
            adapter = OpenCodeAdapter(root)

            first_paths = adapter.generate(self.specs)
            first = {path.relative_to(root): path.read_bytes() for path in first_paths}
            first_prompts = {
                path.relative_to(root): path.read_bytes()
                for path in (root / ".generated" / "prompts").glob("*.md")
            }
            second_paths = adapter.generate(self.specs)
            second = {path.relative_to(root): path.read_bytes() for path in second_paths}
            second_prompts = {
                path.relative_to(root): path.read_bytes()
                for path in (root / ".generated" / "prompts").glob("*.md")
            }

            self.assertEqual(first, second)
            self.assertEqual(first_prompts, second_prompts)
            self.assertFalse((root / ".generated" / "codex").exists())


if __name__ == "__main__":
    unittest.main()
