import json
import shutil
import tempfile
import tomllib
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from runtime.codex.adapter import CodexAdapter
from runtime.common import normalization
from runtime.common.normalization import children_by_parent, load_normalized_agents
from runtime.opencode.adapter import OpenCodeAdapter


class CodexAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.specs = load_normalized_agents()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.output = self.root / ".generated" / "codex"
        self.adapter = CodexAdapter(self.root, environ={})

    def report(self, plan):
        return json.loads(plan.files[self.output / "runtime.json"])

    def native_agent(self, plan, name):
        return tomllib.loads(plan.files[self.output / "agents" / f"{name}.toml"].decode())

    def test_consumes_normalized_agents_without_reopening_canonical_files(self):
        self.assertFalse((self.root / "agents").exists())
        with patch.object(Path, "read_text", side_effect=AssertionError("must use normalized prompts")):
            plan = self.adapter.plan(self.specs)
        self.assertEqual(self.adapter.name, "codex")
        self.assertEqual(set(self.report(plan)["agents"]), set(self.specs))
        self.assertFalse(self.output.exists())

    def test_generation_and_agents_instructions_are_order_independent(self):
        first = self.adapter.plan(self.specs)
        second = self.adapter.plan(dict(reversed(list(self.specs.items()))))
        self.assertEqual(first.files, second.files)
        self.adapter.generate(self.specs)
        before = {p.relative_to(self.root): p.read_bytes() for p in first.files}
        self.adapter.generate(self.specs)
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes() for p in first.files})
        self.assertEqual(self.adapter.plan(self.specs).changes(), {})

    def test_native_agent_files_are_valid_toml_and_embed_normalized_instructions(self):
        plan = self.adapter.plan(self.specs)
        for name, spec in self.specs.items():
            with self.subTest(agent=name):
                native = self.native_agent(plan, name)
                self.assertEqual(native["name"], name)
                self.assertEqual(native["description"], spec.description)
                self.assertIn(spec.prompt, native["developer_instructions"])
                self.assertTrue(spec.default_prompt)
                self.assertIn(spec.default_prompt, native["developer_instructions"])
                self.assertEqual(native["model_reasoning_effort"], spec.tier)
                self.assertNotIn("model", native)

    def test_model_mapping_is_configurable_for_each_tier(self):
        env = {f"CODEX_MODEL_{tier.upper()}": f"configured-{tier}" for tier in ("low", "medium", "high")}
        plan = CodexAdapter(self.root, environ=env).plan(self.specs)
        for name, spec in self.specs.items():
            self.assertEqual(self.report(plan)["agents"][name]["model"], f"configured-{spec.tier}")
            self.assertEqual(self.native_agent(plan, name)["model"], f"configured-{spec.tier}")

    def test_per_agent_overrides_precede_extensions_and_tier_mapping(self):
        builder = replace(self.specs["builder"], extensions={"opencode": {}, "codex": {"model": "extension-model", "reasoning": "high"}})
        specs = {**self.specs, "builder": builder}
        env = {f"CODEX_MODEL_{builder.tier.upper()}": "tier-model", f"CODEX_REASONING_{builder.tier.upper()}": "low"}
        plan = CodexAdapter(self.root, environ=env).plan(specs)
        self.assertEqual(self.native_agent(plan, "builder")["model"], "extension-model")
        self.assertEqual(self.native_agent(plan, "builder")["model_reasoning_effort"], "high")
        env.update(CODEX_MODEL_BUILDER="agent-model", CODEX_REASONING_BUILDER="xhigh")
        plan = CodexAdapter(self.root, environ=env).plan(specs)
        self.assertEqual(self.native_agent(plan, "builder")["model"], "agent-model")
        self.assertEqual(self.native_agent(plan, "builder")["model_reasoning_effort"], "xhigh")

    def test_invalid_reasoning_fails_before_writing(self):
        with self.assertRaises(ValueError):
            CodexAdapter(self.root, environ={"CODEX_REASONING_BUILDER": "imaginary"}).generate(self.specs)
        self.assertFalse(self.output.exists())

    def test_invalid_codex_extensions_fail_without_writing(self):
        for extension in ([], {"unsupported": True}, {"model": " "}, {"model": "invalid model"}, {"reasoning": 3}, {"reasoning": "unknown"}):
            with self.subTest(extension=extension):
                specs = {**self.specs, "builder": replace(self.specs["builder"], extensions={"opencode": {}, "codex": extension})}
                with self.assertRaises(ValueError):
                    self.adapter.generate(specs)
                self.assertEqual(list(self.root.iterdir()), [])

    def test_common_normalization_rejects_malformed_codex_namespace(self):
        source_root = Path(__file__).resolve().parents[1]
        shutil.copytree(source_root / "agents", self.root / "agents")
        config_path = self.root / "agents" / "builder" / "agent.json"
        config = json.loads(config_path.read_text())
        with patch.multiple(normalization, ROOT=self.root, AGENTS_DIR=self.root / "agents", DEFAULTS_DIR=self.root / "agents" / "_defaults"):
            for extension in ([], "invalid", None, True):
                with self.subTest(extension=extension):
                    config_path.write_text(json.dumps({**config, "codex": extension}))
                    with self.assertRaises(SystemExit):
                        normalization.load_normalized_agents()
            config_path.write_text(json.dumps({**config, "codex": {"model": "configured-builder", "reasoning": "high"}}))
            spec = normalization.load_normalized_agents()["builder"]
            self.assertEqual(spec.extensions["codex"], {"model": "configured-builder", "reasoning": "high"})
        self.assertFalse(self.output.exists())

    def test_missing_codex_extension_inherits_runtime_model(self):
        specs = {name: replace(spec, extensions={"opencode": {}}) for name, spec in self.specs.items()}
        report = self.report(self.adapter.plan(specs))
        self.assertTrue(all(agent["model"] is None for agent in report["agents"].values()))

    def test_codex_extension_does_not_leak_into_opencode(self):
        changed = {name: replace(spec, extensions={**spec.extensions, "codex": {"model": "codex-only", "reasoning": "xhigh"}}) for name, spec in self.specs.items()}
        adapter = OpenCodeAdapter()
        for v2 in (False, True):
            self.assertEqual(adapter.build(self.specs, v2=v2), adapter.build(changed, v2=v2))

    def test_opencode_extension_does_not_leak_into_codex(self):
        changed = {name: replace(spec, extensions={**spec.extensions, "opencode": {"temperature": 0.987, "runtime_only_sentinel": "opencode"}}) for name, spec in self.specs.items()}
        self.assertEqual(self.adapter.plan(self.specs).files, self.adapter.plan(changed).files)

    def test_delegation_uses_parent_graph_and_disables_native_leaf_delegation(self):
        plan = self.adapter.plan(self.specs)
        children = children_by_parent(self.specs)
        for name, spec in self.specs.items():
            report = self.report(plan)["agents"][name]
            self.assertEqual(report["parents"], list(spec.parents))
            self.assertEqual(report["children"], children[name])
            if not children[name]:
                self.assertFalse(self.native_agent(plan, name)["agents"]["enabled"])
        modified = {**self.specs, "builder": replace(self.specs["builder"], parents=("review-lead",))}
        report = self.report(self.adapter.plan(modified))
        self.assertIn("builder", report["agents"]["review-lead"]["children"])
        self.assertNotIn("builder", report["agents"]["orchestrator"]["children"])

    def test_permissions_remain_canonical_with_conservative_native_sandbox(self):
        plan = self.adapter.plan(self.specs)
        report = self.report(plan)
        self.assertTrue(report["warnings"])
        for name, spec in self.specs.items():
            expected = "workspace-write" if spec.permissions["edit"] == "allow" else "read-only"
            self.assertEqual(report["agents"][name]["permissions"], spec.permissions)
            self.assertEqual(self.native_agent(plan, name)["sandbox_mode"], expected)
        instructions = self.native_agent(plan, "builder")["developer_instructions"]
        self.assertIn("git reset --hard", instructions)
        self.assertIn("git push --force", instructions)
        self.assertIn("deny", instructions.lower())

    def test_generated_bundle_is_contained_compact_and_marked(self):
        plan = self.adapter.plan(self.specs)
        for path, content in plan.files.items():
            self.assertTrue(path.is_relative_to(self.output))
            if path.suffix in {".md", ".toml"}:
                self.assertIn("GENERATED", content.decode())
                self.assertIn("DO NOT EDIT", content.decode())
        self.assertLess(len(plan.files[self.output / "AGENTS.md"]), 20000)
        self.assertFalse((self.root / "AGENTS.md").exists())

    def test_generation_is_local_without_memory_mcp_or_invented_skills(self):
        with patch("socket.create_connection", side_effect=AssertionError("network forbidden")):
            paths = self.adapter.generate(self.specs)
        self.assertTrue(paths)
        self.assertEqual(self.report(self.adapter.plan(self.specs))["skills"], [])
        self.assertFalse((self.output / "memory-context.md").exists())
        self.assertFalse((self.output / "skills").exists())
        for path in self.output.rglob("*.toml"):
            self.assertNotIn("mcp_servers", tomllib.loads(path.read_text()))


if __name__ == "__main__":
    unittest.main()
