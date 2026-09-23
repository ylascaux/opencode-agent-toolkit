import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class OpenCodeLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.toolkit = self.base / "toolkit"
        self.scripts = self.toolkit / "scripts"
        self.scripts.mkdir(parents=True)
        shutil.copy2(ROOT / "scripts/opencode-agents", self.scripts / "opencode-agents")
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.project = self.base / "project"
        self.project.mkdir()
        self.env = os.environ.copy()
        for key in list(self.env):
            if key.startswith(("OPENCODE_", "OAT_", "MODEL_")):
                self.env.pop(key)
        self.env.update(PATH=f"{self.bin}:{self.env.get('PATH', '')}", HOME=str(self.base / "home"))

        self.write_script("configure-local", "")
        self.write_script("resolve-models", "print('export MODEL_BUILDER=test/medium')\n")
        self.write_script("configure-memory", "")
        self.write_script("opencode-skill-source", "print('{}')\n")

        native = self.bin / "opencode"
        native.write_text(
            "#!/usr/bin/env python3\n"
            "import json,os,sys\n"
            "print(json.dumps({"
            "'binary': os.path.basename(sys.argv[0]),"
            "'args': sys.argv[1:],"
            "'config': os.environ.get('OPENCODE_CONFIG'),"
            "'model': os.environ.get('MODEL_BUILDER'),"
            "'cwd': os.getcwd()"
            "}))\n"
        )
        native.chmod(0o755)
        (self.bin / "oc").symlink_to(self.scripts / "opencode-agents")
        (self.toolkit / ".env").write_text("OAT_RUNTIME=docker\nOAT_SANDBOX_ENABLED=1\nPLAN_APPROVAL_MODE=always\n")

    def write_script(self, name, body):
        (self.scripts / name).write_text("#!/usr/bin/env python3\n" + body)

    def launch(self, *args):
        return subprocess.run([str(self.bin / "oc"), *args], cwd=self.project, env=self.env, capture_output=True, text=True)

    def output(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_oc_always_launches_released_opencode_binary(self):
        output = self.output(self.launch("run", "hello"))
        self.assertEqual(output["binary"], "opencode")
        self.assertEqual(output["args"], ["--standalone", "run", "hello"])
        self.assertEqual(Path(output["config"]).resolve(), self.toolkit / "opencode.jsonc")
        self.assertEqual(output["model"], "test/medium")

    def test_server_commands_are_not_forced_standalone(self):
        for args in (("serve", "--port", "4096"), ("plugin", "list"), ("service", "status")):
            with self.subTest(args=args):
                self.assertEqual(self.output(self.launch(*args))["args"], list(args))

    def test_auth_and_help_bypass_generated_config(self):
        (self.toolkit / ".env").unlink()
        self.write_script("configure-local", "raise SystemExit(91)\n")
        for args in (("auth", "list"), ("--help",), ("--version",)):
            with self.subTest(args=args):
                self.assertEqual(self.output(self.launch(*args))["args"], list(args))

    def test_missing_binary_is_actionable(self):
        self.env["OPENCODE_BIN"] = str(self.base / "missing")
        result = self.launch("run", "hello")
        self.assertEqual(result.returncode, 127)
        self.assertIn("OpenCode 2 binary not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
