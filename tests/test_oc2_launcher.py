import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Oc2LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.toolkit = self.base / "toolkit with spaces"
        self.scripts = self.toolkit / "scripts"
        self.scripts.mkdir(parents=True)
        shutil.copy2(ROOT / "scripts/opencode-agents", self.scripts / "opencode-agents")
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.project = self.base / "project with spaces"
        self.project.mkdir()
        self.env = os.environ.copy()
        for key in list(self.env):
            if key.startswith(("OPENCODE_", "OAT_", "MODEL_")):
                self.env.pop(key)
        self.env.update(PATH=f"{self.bin}:{self.env.get('PATH', '')}", HOME=str(self.base / "home"))
        self.write_script("configure-local", "")
        self.write_script("resolve-models", "print('export MODEL_BUILDER=test/medium')\n")
        self.write_script("opencode-skill-source", "print('{}')\n")
        self.write_script("configure-v2-memory", "")
        for native in ("opencode", "opencode2"):
            file = self.bin / native
            file.write_text("#!/usr/bin/env python3\nimport json,os,sys\nprint(json.dumps({"
                            "'binary': os.path.basename(sys.argv[0]), 'args': sys.argv[1:],"
                            "'cwd': os.getcwd(), 'home': os.environ['HOME'],"
                            "'config': os.environ.get('OPENCODE_CONFIG'),"
                            "'major': os.environ.get('OPENCODE_MAJOR'),"
                            "'model': os.environ.get('MODEL_BUILDER'),"
                            "'v2_memory': os.environ.get('OAT_NATIVE_V2_MEMORY_PLUGIN')}))\n"
                            "sys.exit(int(os.environ.get('FAKE_EXIT', '0')))\n")
            file.chmod(0o755)
        for name in ("oc", "oc2"):
            (self.bin / name).symlink_to(self.scripts / "opencode-agents")
        # A stale Docker installation must not pull the native launchers back into Docker.
        (self.toolkit / ".env").write_text("OPENCODE_MAJOR=1\nOAT_RUNTIME=docker\nOAT_SANDBOX_ENABLED=1\nOPENCODE_PREFLIGHT=1\nPLAN_APPROVAL_MODE=always\n")
        for name in ("docker", "podman", "npm", "pip"):
            file = self.bin / name
            file.write_text("#!/bin/sh\necho UNEXPECTED_RUNTIME >&2\nexit 99\n")
            file.chmod(0o755)

    def write_script(self, name, body):
        (self.scripts / name).write_text("#!/usr/bin/env python3\n" + body)

    def launch(self, *args, command="oc2"):
        return subprocess.run([str(self.bin / command), *args], cwd=self.project,
                              env=self.env, capture_output=True, text=True)

    def output(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_oc2_forces_v2_and_ignores_obsolete_docker_controls(self):
        output = self.output(self.launch("run", "hello"))
        self.assertEqual(output["binary"], "opencode2")
        self.assertEqual(output["major"], "2")
        self.assertEqual(output["args"], ["--standalone", "run", "hello"])
        self.assertEqual(Path(output["config"]).resolve(), self.toolkit / "opencode.v2.jsonc")
        self.assertEqual(output["v2_memory"], "opencode-mem@2.26.0")

    def test_oc_is_always_native_v1(self):
        self.env["OPENCODE_MAJOR"] = "2"
        output = self.output(self.launch("run", "hello", command="oc"))
        self.assertEqual(output["binary"], "opencode")
        self.assertEqual(output["args"], ["run", "hello"])

    def test_explicit_v2_override_wins_for_direct_script(self):
        self.env["OPENCODE_MAJOR"] = "2"
        result = subprocess.run(["bash", str(self.scripts / "opencode-agents"), "run", "hello"],
                                env=self.env, cwd=self.project, text=True, capture_output=True)
        self.assertEqual(self.output(result)["binary"], "opencode2")

    def test_cwd_home_and_argument_boundaries_are_preserved(self):
        output = self.output(self.launch("run", "a prompt with spaces", "", "--file", "a b.txt"))
        self.assertEqual(output["args"], ["--standalone", "run", "a prompt with spaces", "", "--file", "a b.txt"])
        self.assertEqual(output["cwd"], str(self.project))
        self.assertEqual(output["home"], self.env["HOME"])
        self.assertEqual(output["model"], "test/medium")

    def test_auth_and_help_need_neither_env_nor_generated_configuration(self):
        (self.toolkit / ".env").unlink()
        self.write_script("configure-local", "raise SystemExit(91)\n")
        for args in (("auth", "login"), ("auth", "list"), ("--help",), ("--version",)):
            with self.subTest(args=args):
                self.assertEqual(self.output(self.launch(*args))["args"], list(args))

    def test_oc2_memory_can_be_disabled_without_affecting_launcher(self):
        self.env["OAT_OC2_MEMORY_ENABLED"] = "0"
        output = self.output(self.launch("run", "hello"))
        self.assertIsNone(output["v2_memory"])

    def test_explicit_server_and_standalone_are_not_rewritten(self):
        for args in (("--server", "http://localhost:4096", "run", "hello"),
                     ("--standalone", "run", "hello"), ("serve", "--port", "4096")):
            with self.subTest(args=args):
                self.assertEqual(self.output(self.launch(*args))["args"], list(args))

    def test_custom_binary_and_exit_status_are_preserved(self):
        self.env["OPENCODE_BIN"] = str(self.bin / "opencode")
        self.env["FAKE_EXIT"] = "23"
        result = self.launch("run", "hello")
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertEqual(json.loads(result.stdout)["binary"], "opencode")

    def test_failed_generation_model_resolution_and_inline_config_fail_immediately(self):
        for script in ("configure-local", "resolve-models", "opencode-skill-source"):
            with self.subTest(script=script):
                previous = (self.scripts / script).read_text()
                self.write_script(script, "raise SystemExit(47)\n")
                result = self.launch("run", "hello")
                self.assertEqual(result.returncode, 47, result.stderr)
                self.assertEqual(result.stdout, "")
                (self.scripts / script).write_text(previous)

    def test_sync_codex_and_memory_mcp_bypass_runtime_setup(self):
        (self.toolkit / ".env").write_text("exit 88\n")
        for script, args in (("sync-runtime", ("sync", "codex", "--dry-run")),
                             ("codex", ("codex", "doctor")),
                             ("memory-mcp", ("memory", "mcp", "--help"))):
            self.write_script(script, "import json,sys\nprint(json.dumps(sys.argv[1:]))\n")
            result = self.launch(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), list(args[2:] if script == "memory-mcp" else args[1:]))

    def test_missing_native_binary_has_actionable_error(self):
        self.env["OPENCODE_BIN"] = str(self.base / "missing-opencode")
        result = self.launch("run", "hello")
        self.assertEqual(result.returncode, 127)
        self.assertIn("Native OpenCode binary not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
