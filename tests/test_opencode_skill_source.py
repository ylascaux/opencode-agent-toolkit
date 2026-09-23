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

    def test_without_prepared_memory_only_skills_are_added(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp) / "skills"
            skills.mkdir()
            env = os.environ.copy()
            for key in list(env):
                if key.startswith("OAT_AI_MEMORY_") or key == "OPENCODE_CONFIG_CONTENT":
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
            self.assertNotIn("mcp", config)
            self.assertNotIn("instructions", config)


if __name__ == "__main__":
    unittest.main()
