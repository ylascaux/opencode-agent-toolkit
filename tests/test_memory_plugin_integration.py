from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "memory_plugin.py"
spec = importlib.util.spec_from_file_location("memory_plugin", MODULE_PATH)
assert spec and spec.loader
memory_plugin = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = memory_plugin
spec.loader.exec_module(memory_plugin)


class MemoryPluginIntegrationTests(unittest.TestCase):
    def test_default_settings_point_to_external_plugin_repo(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            settings = memory_plugin.PluginSettings.from_env()
        self.assertEqual(settings.repo, "git@github.com:ylascaux/opencode-memory-plugin.git")
        self.assertEqual(settings.ref, "main")
        self.assertTrue(str(settings.directory).endswith("opencode-agent-toolkit/plugins/opencode-memory-plugin"))

    def test_existing_unmanaged_checkout_builds_and_returns_dist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "plugin"
            scripts = plugin / "scripts"
            scripts.mkdir(parents=True)
            (scripts / "build.mjs").write_text(textwrap.dedent(
                """
                import { mkdir, writeFile } from "node:fs/promises";
                await mkdir("dist", { recursive: true });
                for (const file of ["v1.js", "v2.js", "cli.js"]) await writeFile(`dist/${file}`, "export default {}\\n");
                """
            ).strip() + "\n")
            settings = memory_plugin.PluginSettings(
                repo="",
                ref="main",
                directory=plugin,
                auto_sync=False,
                sync_interval_seconds=300,
                strict=True,
            )
            resolved = memory_plugin.ensure_plugin(settings=settings)
            self.assertEqual(resolved, plugin)
            for filename in ("v1.js", "v2.js", "cli.js"):
                self.assertTrue((plugin / "dist" / filename).is_file())

    def test_cli_command_uses_built_external_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "plugin"
            (plugin / "dist").mkdir(parents=True)
            (plugin / "dist" / "v1.js").write_text("export default {}\n")
            (plugin / "dist" / "v2.js").write_text("export default {}\n")
            (plugin / "dist" / "cli.js").write_text("console.log('ok')\n")
            settings = memory_plugin.PluginSettings(
                repo="",
                ref="main",
                directory=plugin,
                auto_sync=False,
                sync_interval_seconds=300,
                strict=True,
            )
            with mock.patch.object(memory_plugin.PluginSettings, "from_env", return_value=settings):
                command = memory_plugin.cli_command("render", "--agent", "orchestrator")
            self.assertEqual(command[0], "node")
            self.assertEqual(Path(command[1]), plugin / "dist" / "cli.js")
            self.assertEqual(command[2:], ["render", "--agent", "orchestrator"])


if __name__ == "__main__":
    unittest.main()
