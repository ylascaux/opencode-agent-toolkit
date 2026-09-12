from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("memory_plugin_mcp_tests", ROOT / "scripts" / "memory_plugin.py")
assert spec and spec.loader
plugin = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = plugin
spec.loader.exec_module(plugin)


class MemoryMcpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.toolkit = self.root / "toolkit"
        scripts = self.toolkit / "scripts"
        scripts.mkdir(parents=True)
        for name in ("memory-mcp", "memory_plugin.py", "memory", "opencode-agents"):
            shutil.copy2(ROOT / "scripts" / name, scripts / name)
        (self.toolkit / "config").mkdir()
        shutil.copy2(ROOT / "config" / "plugins.json", self.toolkit / "config" / "plugins.json")
        self.workspace = self.root / "workspace with spaces"
        self.workspace.mkdir()
        self.external = self.root / "plugin"
        (self.external / "dist").mkdir(parents=True)
        for name in ("mcp.js", "service.js"):
            (self.external / "dist" / name).write_text("// fixture adapter\n")
        (self.external / "dist" / "cli.js").write_text(
            "console.log(JSON.stringify({jsonrpc:'2.0',id:1,result:{args:process.argv.slice(2),"
            "cwd:process.cwd(),enabled:process.env.OAT_MEMORY_ENABLED||'',sentinel:process.env.PROFILE_SENTINEL||''}}));\n"
        )
        (self.external / "scripts").mkdir()
        (self.external / "scripts" / "build.mjs").write_text("throw new Error('must not build');\n")
        self.env = {key: value for key, value in os.environ.items() if not key.startswith(("OAT_", "OPENCODE_MEMORY_"))}
        self.env.update(OAT_MEMORY_PLUGIN_DIR=str(self.external), OAT_MEMORY_ENABLED="1", PYTHONDONTWRITEBYTECODE="1")

    def run_wrapper(self, args=(), *, launcher=False, human=False):
        if launcher:
            command = ["bash", str(self.toolkit / "scripts" / "opencode-agents"), "memory", "mcp"]
        else:
            command = [sys.executable, "-B", str(self.toolkit / "scripts" / ("memory" if human else "memory-mcp"))]
            if human:
                command.append("mcp")
        return subprocess.run([*command, *args], cwd=self.workspace, env=self.env, text=True, capture_output=True)

    def test_wrapper_executes_only_existing_external_cli_and_keeps_stdio_clean(self):
        before = sorted(p.relative_to(self.root) for p in self.root.rglob("*"))
        result = self.run_wrapper(["--cwd", str(self.workspace)])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["result"]["args"], ["mcp", "--cwd", str(self.workspace.resolve())])
        self.assertEqual(payload["result"]["enabled"], "1")
        self.assertEqual(sorted(p.relative_to(self.root) for p in self.root.rglob("*")), before)

    def test_oc_mcp_routes_before_profiles_docker_or_opencode(self):
        (self.toolkit / ".env").write_text("echo PROFILE_MUST_NOT_RUN\nexit 90\n")
        (self.toolkit / ".env.local").write_text("echo LOCAL_PROFILE_MUST_NOT_RUN\nexit 91\n")
        self.env.update(OAT_RUNTIME="docker", OPENCODE_BIN="must-not-run", PROFILE_SENTINEL="exported")
        result = self.run_wrapper(launcher=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["result"]["sentinel"], "exported")
        self.assertEqual(Path(payload["result"]["cwd"]).resolve(), self.workspace.resolve())

    def test_direct_human_script_mcp_preserves_no_install_route(self):
        result = self.run_wrapper(human=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["result"]["args"][0], "mcp")

    def test_missing_plugin_or_capability_fails_without_building_or_installing(self):
        (self.external / "dist" / "mcp.js").unlink()
        result = self.run_wrapper()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("built external plugin lacks MCP support", result.stderr)
        self.assertFalse((self.external / "dist" / "mcp.js").exists())
        self.env["OAT_MEMORY_PLUGIN_DIR"] = str(self.root / "missing")
        result = self.run_wrapper()
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.root / "missing").exists())

    def test_missing_node_fails_without_installing(self):
        with mock.patch.dict(os.environ, self.env, clear=True), mock.patch.object(plugin.shutil, "which", return_value=None):
            with self.assertRaisesRegex(SystemExit, "Node.js is required"):
                plugin.mcp_command(self.workspace)

    def test_invalid_paths_arguments_and_settings_never_echo_values(self):
        token = "github_pat_synthetic_fixture_token_123456789"
        for args in ([f"--{token}"], ["--cwd"], ["--cwd", str(self.root / token)]):
            result = self.run_wrapper(args)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertNotIn(token, result.stderr)
            self.assertNotIn("Traceback", result.stderr)
        self.env["OAT_MEMORY_PLUGIN_SYNC_INTERVAL_SECONDS"] = token
        result = self.run_wrapper()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(token, result.stderr)

    def test_symlink_loop_reports_safe_error(self):
        loop = self.root / "github_pat_synthetic_loop_123456789"
        loop.symlink_to(loop)
        self.env["OAT_MEMORY_PLUGIN_DIR"] = str(loop)
        result = self.run_wrapper()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertNotIn(loop.name, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_mcp_resolution_cannot_call_network_build_or_vault_helpers(self):
        with mock.patch.dict(os.environ, self.env, clear=True), \
             mock.patch.object(plugin, "ensure_plugin", side_effect=AssertionError("install forbidden")), \
             mock.patch.object(plugin, "_git", side_effect=AssertionError("git forbidden")), \
             mock.patch.object(plugin, "_run", side_effect=AssertionError("build forbidden")):
            command = plugin.mcp_command(self.workspace)
        self.assertEqual(command[2:], ["mcp", "--cwd", str(self.workspace.resolve())])


if __name__ == "__main__":
    unittest.main()
