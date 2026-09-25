import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class OneCommandInstallTests(unittest.TestCase):
    def test_just_install_routes_through_bootstrap(self):
        text = (ROOT / "justfile").read_text()
        install = text.split("\ninstall:\n", 1)[1].split("\n\n", 1)[0]
        self.assertIn("bash ./scripts/bootstrap", install)

    def test_existing_opencode_is_preserved_before_any_npm_action(self):
        text = (ROOT / "scripts/bootstrap").read_text()
        detect = text.index("if command -v opencode")
        npm = text.index("npm uninstall -g opencode-ai")
        self.assertLess(detect, npm)
        self.assertIn("OpenCode already installed", text)
        self.assertIn("Keeping existing OpenCode version", text)
        self.assertIn('bash "$ROOT/scripts/user-link" install oc', text)
        self.assertIn('opencode plugin remove "$target"', text)
        self.assertIn("@rehydra/opencode(@[^[:space:]]+)?", text)
        self.assertIn('bash "$ROOT/scripts/user-link" uninstall oc2', text)
        self.assertNotIn('user-link" install oc2', text)

    def test_missing_opencode_can_be_installed_with_npm(self):
        text = (ROOT / "scripts/bootstrap").read_text()
        self.assertIn("npm install -g @opencode/cli@latest", text)
        self.assertIn("OpenCode is not installed and npm is unavailable", text)

    def test_native_memory_plugin_is_installed_and_v2_runtime_is_prepared(self):
        text = (ROOT / "scripts/bootstrap").read_text()
        self.assertIn('OAT_MEMORY_DIR:-$HOME/opencode-memory', text)
        self.assertIn('https://github.com/ylascaux/opencode-memory.git', text)
        self.assertIn('scripts/memory_plugin.py', text)
        self.assertIn('OAT_MEMORY_CAPTURE_ENABLED', text)
        self.assertIn('OAT_AI_MEMORY_', text, "bootstrap must migrate the short-lived legacy variables")
        self.assertIn('scripts/v2-python', text)
        self.assertIn('memory_backend="${OAT_MEMORY_BACKEND:-local}"', text)
        self.assertIn('OAT_MEMORY_DIR:-$HOME/opencode-memory', text, "legacy backend remains explicitly available")

    def test_install_retargets_stale_launcher_from_old_toolkit_clone(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "old" / "opencode-agent-toolkit"
            new = root / "new" / "opencode-agent-toolkit"
            bindir = root / "bin"
            for toolkit in (old, new):
                (toolkit / "scripts").mkdir(parents=True)
                (toolkit / "scripts" / "opencode-agents").write_text("#!/usr/bin/env bash\nexport OAT_RUNTIME=host\n")
                (toolkit / "justfile").write_text("install:\n    bash ./scripts/bootstrap\n")
            shutil.copy2(ROOT / "scripts" / "user-link", new / "scripts" / "user-link")
            bindir.mkdir()
            (bindir / "oc").symlink_to(old / "scripts" / "opencode-agents")

            env = os.environ.copy()
            env["OPENCODE_TOOLKIT_BIN_DIR"] = str(bindir)
            result = subprocess.run(
                ["bash", str(new / "scripts" / "user-link"), "install", "oc"],
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(os.readlink(bindir / "oc"), str(new / "scripts" / "opencode-agents"))
            self.assertIn("Retargeted stale toolkit launcher", result.stdout)

    def test_bootstrap_remains_valid_bash(self):
        result = subprocess.run(["bash", "-n", str(ROOT / "scripts/bootstrap")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
