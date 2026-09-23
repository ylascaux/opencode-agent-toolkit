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
    return SimpleNamespace(
        name=name,
        description=f"Role {name}",
        mode="primary" if primary else "subagent",
        parents=parents,
        model_env="MODEL_" + name.upper().replace("-", "_"),
        permissions={"bash": {"*": "ask", "terraform destroy*": "deny"}, "edit": "allow"},
        prompt="Specialist instructions." if parents == ("orchestrator",) else "PLAN_APPROVAL_REQUIRED",
        extensions={"opencode": {}},
    )


class NativeConfigTests(unittest.TestCase):
    def setUp(self):
        self.agents = {
            "meta-router": agent("meta-router", primary=True),
            "orchestrator": agent("orchestrator", ("meta-router",)),
            "builder": agent("builder", ("orchestrator",)),
        }

    def test_open_code_2_config_uses_native_schema_and_memory_plugin(self):
        config = native.render_config(self.agents)
        self.assertEqual(config["default_agent"], "meta-router")
        self.assertEqual(config["agents"]["builder"]["model"], "{env:MODEL_BUILDER}")
        self.assertEqual(config["plugins"], ["-rehydra", "-rehydra.*", "oc2-memory@0.1.1"])
        self.assertIn(
            {"action": "subagent", "resource": "orchestrator", "effect": "allow"},
            config["agents"]["meta-router"]["permissions"],
        )
        self.assertIn(
            {"action": "shell", "resource": "terraform destroy*", "effect": "deny"},
            config["agents"]["builder"]["permissions"],
        )
        self.assertNotIn("PLAN_APPROVAL_REQUIRED", json.dumps(config))
        self.assertNotIn('"ask"', json.dumps(config))

    def test_native_git_is_usable_but_specific_destructive_denials_remain(self):
        source = {"bash": {"*": "ask", "git push*": "deny", "aws *": "deny", "git push --force*": "deny"}}
        rendered = native.native_permissions(source)
        self.assertEqual(rendered["bash"]["git push*"], "allow")
        self.assertEqual(rendered["bash"]["aws *"], "allow")
        self.assertEqual(rendered["bash"]["git push --force*"], "deny")
        self.assertEqual(source["bash"]["git push*"], "deny")

    def test_source_permissions_are_not_modified_for_codex_sync(self):
        native.render_config(self.agents)
        self.assertEqual(self.agents["builder"].permissions["bash"]["*"], "ask")
        self.assertEqual(self.agents["meta-router"].prompt, "PLAN_APPROVAL_REQUIRED")

    def test_single_config_is_self_contained_and_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = SimpleNamespace(description="Review a patch", prompt="Check the patch and report findings.")
            files = native.render_files(root, self.agents, {"review": skill})
            native.write_files(files)
            self.assertEqual(set(files), {root / "opencode.jsonc", root / ".opencode/skills/review/SKILL.md"})
            before = {path: path.stat().st_mtime_ns for path in files}
            native.write_files(files)
            self.assertEqual(before, {path: path.stat().st_mtime_ns for path in files})
            json.loads((root / "opencode.jsonc").read_text())
            self.assertFalse((root / "opencode.v2.jsonc").exists())

    def test_reserved_overrides_do_not_silently_replace_models_or_policy(self):
        self.agents["builder"].extensions["opencode"]["model"] = "wrong/model"
        with self.assertRaises(ValueError):
            native.render_config(self.agents)


if __name__ == "__main__":
    unittest.main()
