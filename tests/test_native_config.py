import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
module_spec = importlib.util.spec_from_file_location("native_config", ROOT / "scripts/native_config.py")
native = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(native)


def agent(name, parents=(), primary=False):
    return SimpleNamespace(name=name, description=f"Role {name}", mode="primary" if primary else "subagent",
                           parents=parents, model_env="MODEL_" + name.upper().replace("-", "_"),
                           permissions={"bash": {"*": "ask", "terraform destroy*": "deny"}, "edit": "allow"},
                           prompt="Specialist instructions." if parents == ("orchestrator",) else "PLAN_APPROVAL_REQUIRED",
                           extensions={"opencode": {}})


class NativeConfigTests(unittest.TestCase):
    def setUp(self):
        self.agents = {"meta-router": agent("meta-router", primary=True),
                       "orchestrator": agent("orchestrator", ("meta-router",)),
                       "builder": agent("builder", ("orchestrator",))}

    def test_v1_v2_keep_models_meta_and_delegation_without_plugins_or_caps(self):
        for v2 in (False, True):
            with self.subTest(v2=v2):
                config = native.render_config(self.agents, v2=v2)
                self.assertEqual(config["default_agent"], "meta-router")
                agents = config["agents" if v2 else "agent"]
                self.assertEqual(agents["builder"]["model"], "{env:MODEL_BUILDER}")
                self.assertNotIn("steps", agents["builder"])
                self.assertNotIn("shell", config)
                self.assertEqual(config["plugins" if v2 else "plugin"], [])
                self.assertNotIn("PLAN_APPROVAL_REQUIRED", json.dumps(config))
                self.assertIn("Specialist instructions.", json.dumps(config))
                if v2:
                    self.assertIn({"action": "subagent", "resource": "orchestrator", "effect": "allow"}, agents["meta-router"]["permissions"])
                    self.assertIn({"action": "shell", "resource": "terraform destroy*", "effect": "deny"}, agents["builder"]["permissions"])
                else:
                    self.assertEqual(agents["meta-router"]["permission"]["task"]["orchestrator"], "allow")
                    self.assertEqual(agents["builder"]["permission"]["bash"]["terraform destroy*"], "deny")
                self.assertNotIn('"ask"', json.dumps(config))

    def test_native_git_is_usable_but_specific_destructive_denials_remain(self):
        source = {"bash": {"*": "ask", "git push*": "deny", "aws *": "deny", "git push --force*": "deny"}}
        rendered = native.native_permissions(source)
        self.assertEqual(rendered["bash"]["git push*"], "allow")
        self.assertEqual(rendered["bash"]["aws *"], "allow")
        self.assertEqual(rendered["bash"]["git push --force*"], "deny")
        self.assertEqual(source["bash"]["git push*"], "deny")

    def test_source_permissions_are_not_modified_for_codex_sync(self):
        native.render_config(self.agents, v2=True)
        self.assertEqual(self.agents["builder"].permissions["bash"]["*"], "ask")
        self.assertEqual(self.agents["meta-router"].prompt, "PLAN_APPROVAL_REQUIRED")

    def test_configs_are_self_contained_and_writes_are_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = SimpleNamespace(description="Review a patch", prompt="Check the patch and report findings.")
            files = native.render_files(root, self.agents, {"review": skill})
            native.write_files(files)
            before = {path: path.stat().st_mtime_ns for path in files}
            native.write_files(files)
            self.assertEqual(before, {path: path.stat().st_mtime_ns for path in files})
            for name in ("opencode.jsonc", "opencode.v2.jsonc"):
                self.assertNotIn("{file:", (root / name).read_text())
                json.loads((root / name).read_text())
            self.assertFalse(list(root.glob(".opencode.*")))

    def test_reserved_overrides_do_not_silently_replace_models_or_policy(self):
        self.agents["builder"].extensions["opencode"]["model"] = "wrong/model"
        with self.assertRaises(ValueError):
            native.render_config(self.agents, v2=True)


if __name__ == "__main__":
    unittest.main()
