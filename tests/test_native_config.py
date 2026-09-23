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

    def test_stable_shape_uses_open_code_2_fields(self):
        config = native.render_config(self.agents)
        self.assertEqual(config["default_agent"], "meta-router")
        self.assertIn("agents", config)
        self.assertIn("commands", config)
        self.assertIn("plugins", config)
        self.assertNotIn("agent", config)
        self.assertNotIn("command", config)
        self.assertNotIn("plugin", config)
        self.assertEqual(config["agents"]["builder"]["model"], "{env:MODEL_BUILDER}")
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

    def test_single_config_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = SimpleNamespace(description="Review a patch", prompt="Check the patch and report findings.")
            files = native.render_files(root, self.agents, {"review": skill})
            native.write_files(files)
            self.assertTrue((root / "opencode.jsonc").is_file())
            self.assertFalse((root / "opencode.v2.jsonc").exists())
            json.loads((root / "opencode.jsonc").read_text())

    def test_reserved_overrides_do_not_replace_runtime_fields(self):
        self.agents["builder"].extensions["opencode"]["model"] = "wrong/model"
        with self.assertRaises(ValueError):
            native.render_config(self.agents)


if __name__ == "__main__":
    unittest.main()
