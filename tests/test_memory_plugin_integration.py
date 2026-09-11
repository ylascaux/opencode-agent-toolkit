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
    def test_default_settings_come_from_external_plugin_config(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            settings = memory_plugin.PluginSettings.from_env()
        self.assertEqual(settings.repo, "git@github.com:ylascaux/opencode-memory-plugin.git")
        self.assertEqual(settings.ref, "5db9868f160cf3f947c3397b5dc8b38f25424274")
        self.assertTrue(str(settings.directory).endswith("opencode-agent-toolkit/plugins/opencode-memory-plugin"))

    def test_environment_can_override_versioned_plugin_config(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "OAT_MEMORY_PLUGIN_REPO": "git@example.invalid/custom-memory-plugin.git",
                "OAT_MEMORY_PLUGIN_REF": "feature/test",
            },
            clear=True,
        ):
            settings = memory_plugin.PluginSettings.from_env()
        self.assertEqual(settings.repo, "git@example.invalid/custom-memory-plugin.git")
        self.assertEqual(settings.ref, "feature/test")

    def test_github_pat_uses_transient_https_rewrite_and_askpass(self) -> None:
        token = "github_pat_test_secret_value"
        env = memory_plugin._git_env(
            {
                "OAT_GITHUB_TOKEN": token,
                "HOME": "/tmp/home",
                "GIT_SSH_COMMAND": "ssh custom",
            }
        )
        self.assertEqual(env["GIT_TERMINAL_PROMPT"], "0")
        self.assertEqual(env["GIT_ASKPASS_REQUIRE"], "force")
        self.assertEqual(env["OAT_GIT_ASKPASS_TOKEN"], token)
        self.assertEqual(env["GIT_CONFIG_COUNT"], "2")
        self.assertEqual(env["GIT_CONFIG_KEY_0"], "url.https://github.com/.insteadOf")
        self.assertEqual(env["GIT_CONFIG_VALUE_0"], "git@github.com:")
        self.assertEqual(env["GIT_CONFIG_KEY_1"], "url.https://github.com/.insteadOf")
        self.assertEqual(env["GIT_CONFIG_VALUE_1"], "ssh://git@github.com/")
        self.assertNotIn("GIT_SSH_COMMAND", env)
        helper = Path(env["GIT_ASKPASS"]).read_text()
        self.assertNotIn(token, helper)
        self.assertIn("OAT_GIT_ASKPASS_TOKEN", helper)

    def test_without_pat_git_stays_noninteractive_ssh(self) -> None:
        env = memory_plugin._git_env({"HOME": "/tmp/home"})
        self.assertEqual(env["GIT_TERMINAL_PROMPT"], "0")
        self.assertEqual(env["GIT_SSH_COMMAND"], "ssh -o BatchMode=yes")
        self.assertNotIn("GIT_ASKPASS", env)

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
