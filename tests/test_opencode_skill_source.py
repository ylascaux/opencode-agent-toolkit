import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "opencode-skill-source"


class OpenCodeSkillSourceTests(unittest.TestCase):
    def test_injects_memory_context_and_mcp_without_losing_user_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            skills = base / "skills"
            skills.mkdir()
            context = base / "context.md"
            context.write_text("# Memory context\n")
            env = os.environ.copy()
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
                    "OAT_AI_MEMORY_CONTEXT_FILE": str(context),
                    "OAT_AI_MEMORY_ADAPTER": "/toolkit/scripts/ai-memory-adapter",
                    "OAT_AI_MEMORY_HOME": "/data/create-ai-memory",
                    "OAT_AI_MEMORY_ROOT": "/data/opencode-memory",
                    "OAT_AI_MEMORY_PROJECT": "demo",
                }
            )
            result = subprocess.run(
                ["python3", str(SOURCE), str(skills)],
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads(result.stdout)
            self.assertIn("/existing.md", config["instructions"])
            self.assertIn(str(context), config["instructions"])
            self.assertIn("existing", config["mcp"]["servers"])
            memory = config["mcp"]["servers"]["oat-memory"]
            self.assertEqual(memory["type"], "local")
            self.assertEqual(memory["protocol"], "legacy")
            self.assertFalse(memory["codemode"])
            self.assertEqual(memory["command"], ["python3", "/toolkit/scripts/ai-memory-adapter", "mcp"])
            self.assertEqual(memory["environment"]["OAT_AI_MEMORY_PROJECT"], "demo")

    def test_without_prepared_memory_context7_is_still_added(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "skills"
            skills.mkdir()
            env = os.environ.copy()
            for key in list(env):
                if key.startswith("OAT_AI_MEMORY_") or key in {"OPENCODE_CONFIG_CONTENT", "CONTEXT7_API_KEY"}:
                    env.pop(key, None)
            result = subprocess.run(
                ["python3", str(SOURCE), str(skills)],
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads(result.stdout)
            self.assertEqual(config["skills"], [str(skills.resolve())])
            context7 = config["mcp"]["servers"]["context7"]
            self.assertEqual(context7, {
                "type": "remote",
                "url": "https://mcp.context7.com/mcp",
            })
            self.assertNotIn("instructions", config)


    def test_context7_api_key_uses_environment_placeholder_not_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "skills"
            skills.mkdir()
            env = os.environ.copy()
            for key in list(env):
                if key.startswith("OAT_AI_MEMORY_") or key == "OPENCODE_CONFIG_CONTENT":
                    env.pop(key, None)
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
            env = os.environ.copy()
            for key in list(env):
                if key.startswith("OAT_AI_MEMORY_") or key in {"OPENCODE_CONFIG_CONTENT", "CONTEXT7_API_KEY"}:
                    env.pop(key, None)
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
            env = os.environ.copy()
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
