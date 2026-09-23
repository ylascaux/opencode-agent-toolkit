import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE_MEMORY = ROOT / "scripts" / "native_memory.py"


class NativeMemoryTests(unittest.TestCase):
    def test_prepares_local_v2_plugin_and_renders_context_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            plugin = base / "plugin"
            dist = plugin / "dist"
            dist.mkdir(parents=True)
            (dist / "v2.js").write_text("export default { id: 'fixture', setup() {} }\n")
            (dist / "cli.js").write_text("console.log('# Rendered memory\\nProject context')\n")
            vault = base / "vault"
            vault.mkdir()
            wrapper = base / "wrapper"
            context = base / "context.md"

            env = os.environ.copy()
            for key in list(env):
                if key.startswith(("OAT_MEMORY_", "OPENCODE_MEMORY_")):
                    env.pop(key, None)
            env.update(
                {
                    "OAT_MEMORY_ENABLED": "1",
                    "OAT_MEMORY_PLUGIN_DIR": str(plugin),
                    "OAT_MEMORY_DIR": str(vault),
                    "OAT_MEMORY_WRAPPER_DIR": str(wrapper),
                }
            )
            result = subprocess.run(
                ["python3", str(NATIVE_MEMORY), "--major", "2", "--context-file", str(context)],
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(result.stdout.strip()), wrapper.resolve())
            self.assertTrue((wrapper / "package.json").is_file())
            self.assertIn((dist / "v2.js").resolve().as_uri(), (wrapper / "index.js").read_text())
            self.assertEqual(context.read_text(), "# Rendered memory\nProject context\n")

    def test_disabled_memory_does_not_create_runtime_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            env = os.environ.copy()
            for key in list(env):
                if key.startswith(("OAT_MEMORY_", "OPENCODE_MEMORY_")):
                    env.pop(key, None)
            env.update(
                {
                    "OAT_MEMORY_ENABLED": "0",
                    "OAT_MEMORY_WRAPPER_DIR": str(base / "wrapper"),
                }
            )
            result = subprocess.run(
                ["python3", str(NATIVE_MEMORY), "--major", "2"],
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertFalse((base / "wrapper").exists())


if __name__ == "__main__":
    unittest.main()
