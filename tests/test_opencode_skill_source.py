import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "opencode-skill-source"


def clean_env():
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(("OAT_MEMORY_", "OAT_AI_MEMORY_", "OPENCODE_MEMORY_")) or key in {
            "OPENCODE_CONFIG_CONTENT",
            "CONTEXT7_API_KEY",
        }:
            env.pop(key, None)
    return env


class OpenCodeSkillSourceTests(unittest.TestCase):
    def test_injects_native_memory_plugin_context_and_mcp_without_losing_user_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            skills = base / "skills"
            skills.mkdir()
            context = base / "context.md"
            context.write_text("# Memory context\n")
            target = base / "memory-wrapper"
            target.mkdir()
            plugin = base / "plugin"
            (plugin / "dist").mkdir(parents=True)
            cli = plugin / "dist" / "cli.js"
            cli.write_text("console.log('fixture')\n")
            env = clean_env()
            env.update(
                {
                    "OPENCODE_CONFIG_CONTENT": json.dumps(
                        {
                            "instructions": ["/existing.md"],
                            "mcp": {
                                "servers": {
                                    "existing": {
                                        "type": "local",
                                        "command": ["existing-server"],
                                    }
                                }
                            },
                        }
                    ),
                    "OAT_MEMORY_PLUGIN_TARGET": str(target),
                    "OAT_MEMORY_CONTEXT_FILE": str(context),
                    "OAT_MEMORY_PLUGIN_DIR": str(plugin),
                    "OAT_MEMORY_ENABLED": "1",
                    "OAT_MEMORY_CAPTURE_ENABLED": "1",
                    "OAT_MEMORY_DIR": str(base / "vault"),
                    "OAT_MEMORY_PROJECT": "demo",
                }
            )
            result = subprocess.run(
                ["python3", str(SOURCE), str(skills)],
                env=env,
                text=True,
                capture_output=True,
                cwd=base,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads(result.stdout)
            self.assertIn("/existing.md", config["instructions"])
            self.assertIn(str(context), config["instructions"])
            self.assertIn(str(target), config["plugins"])
            self.assertIn("existing", config["mcp"]["servers"])
            memory = config["mcp"]["servers"]["oat-memory"]
            self.assertEqual(memory["type"], "local")
            self.assertEqual(memory["command"][:4], ["node", str(cli), "mcp", "--cwd"])
            self.assertEqual(Path(memory["command"][4]).resolve(), base.resolve())
            self.assertEqual(memory["environment"]["OAT_MEMORY_PROJECT"], "demo")
            self.assertEqual(memory["environment"]["OAT_MEMORY_CAPTURE_ENABLED"], "1")

    def test_without_prepared_memory_context7_is_still_added(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "skills"
            skills.mkdir()
            env = clean_env()
            result = subprocess.run(
                ["python3", str(SOURCE), str(skills)],
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads(result.stdout)
            self.assertEqual([Path(value).resolve() for value in config["skills"]], [skills.resolve()])
            context7 = config["mcp"]["servers"]["context7"]
            self.assertEqual(context7, {
                "type": "remote",
                "url": "https://mcp.context7.com/mcp",
            })
            self.assertNotIn("instructions", config)
            self.assertNotIn("plugins", config)

    def test_context7_api_key_uses_environment_placeholder_not_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "skills"
            skills.mkdir()
            env = clean_env()
            env["CONTEXT7_API_KEY"] = "super-secret-test-key"
            result = subprocess.run(
                ["python3", str(SOURCE), str(skills)],
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("super-secret-test-key", result.stdout)
            config = json.loads(result.stdout)
            context7 = config["mcp"]["servers"]["context7"]
            self.assertFalse(context7["oauth"])
            self.assertEqual(
                context7["headers"]["Authorization"],
                "Bearer {env:CONTEXT7_API_KEY}",
            )

    def test_context7_can_be_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "skills"
            skills.mkdir()
            env = clean_env()
            env["OAT_CONTEXT7_ENABLED"] = "0"
            result = subprocess.run(
                ["python3", str(SOURCE), str(skills)],
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads(result.stdout)
            self.assertNotIn("mcp", config)

    def test_user_context7_server_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "skills"
            skills.mkdir()
            env = clean_env()
            env["OPENCODE_CONFIG_CONTENT"] = json.dumps({
                "mcp": {
                    "servers": {
                        "context7": {
                            "type": "remote",
                            "url": "https://example.invalid/custom-context7",
                            "disabled": True,
                        }
                    }
                }
            })
            result = subprocess.run(
                ["python3", str(SOURCE), str(skills)],
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads(result.stdout)
            self.assertEqual(
                config["mcp"]["servers"]["context7"]["url"],
                "https://example.invalid/custom-context7",
            )
            self.assertTrue(config["mcp"]["servers"]["context7"]["disabled"])


if __name__ == "__main__":
    unittest.main()
