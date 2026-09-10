from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExternalMemoryBridgeTests(unittest.TestCase):
    def _fixture(self, tmp: str) -> tuple[Path, Path, dict[str, str]]:
        base = Path(tmp)
        toolkit = base / "toolkit"
        scripts = toolkit / "scripts"
        prompts = toolkit / ".generated" / "prompts"
        config = toolkit / "config"
        plugin = base / "plugin"
        dist = plugin / "dist"
        scripts.mkdir(parents=True)
        prompts.mkdir(parents=True)
        config.mkdir(parents=True)
        dist.mkdir(parents=True)
        shutil.copy2(ROOT / "scripts" / "apply-memory", scripts / "apply-memory")
        shutil.copy2(ROOT / "scripts" / "memory_plugin.py", scripts / "memory_plugin.py")
        shutil.copy2(ROOT / "config" / "plugins.json", config / "plugins.json")
        (toolkit / "opencode.jsonc").write_text(json.dumps({"plugin": ["./runtime/plugins/sandbox-v1.js"]}))
        (toolkit / "opencode.v2.jsonc").write_text(json.dumps({"plugins": []}))
        (prompts / "builder.md").write_text("# Builder\n\nBase prompt.\n")
        (dist / "v1.js").write_text("export const OpenCodeMemoryPlugin = async () => ({})\n")
        (dist / "v2.js").write_text("export default { id: 'memory', async setup() {} }\n")
        (dist / "cli.js").write_text(textwrap.dedent(
            """
            const args = process.argv.slice(2)
            if (args[0] !== "render") process.exit(2)
            const idx = args.indexOf("--agent")
            const agent = idx >= 0 ? args[idx + 1] : "unknown"
            console.log(`## Opt-in long-term memory\\n\\nagent=${agent}`)
            """
        ).strip() + "\n")
        env = os.environ.copy()
        env.update({
            "OAT_MEMORY_ENABLED": "1",
            "OAT_MEMORY_PLUGIN_DIR": str(plugin),
            "OAT_MEMORY_PLUGIN_AUTO_SYNC": "0",
        })
        return toolkit, plugin, env

    def test_bridge_configures_both_runtimes_and_renders_v2_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            toolkit, plugin, env = self._fixture(tmp)
            script = toolkit / "scripts" / "apply-memory"
            first = subprocess.run(["python3", str(script)], cwd=toolkit, env=env, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            v1 = json.loads((toolkit / "opencode.jsonc").read_text())
            v2 = json.loads((toolkit / "opencode.v2.jsonc").read_text())
            self.assertIn(str((plugin / "dist" / "v1.js").resolve()), v1["plugin"])
            self.assertIn(str((plugin / "dist" / "v2.js").resolve()), v2["plugins"])
            prompt = (toolkit / ".generated" / "prompts" / "builder.md").read_text()
            self.assertEqual(prompt.count("## Opt-in long-term memory"), 1)
            self.assertIn("agent=builder", prompt)

            second = subprocess.run(["python3", str(script)], cwd=toolkit, env=env, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            prompt = (toolkit / ".generated" / "prompts" / "builder.md").read_text()
            self.assertEqual(prompt.count("## Opt-in long-term memory"), 1)

            env["OAT_MEMORY_ENABLED"] = "0"
            disabled = subprocess.run(["python3", str(script)], cwd=toolkit, env=env, capture_output=True, text=True)
            self.assertEqual(disabled.returncode, 0, disabled.stderr)
            v1 = json.loads((toolkit / "opencode.jsonc").read_text())
            v2 = json.loads((toolkit / "opencode.v2.jsonc").read_text())
            self.assertFalse(any("opencode-memory-plugin" in value for value in v1["plugin"]))
            self.assertFalse(any("opencode-memory-plugin" in value for value in v2["plugins"]))
            self.assertNotIn("## Opt-in long-term memory", (toolkit / ".generated" / "prompts" / "builder.md").read_text())


if __name__ == "__main__":
    unittest.main()
