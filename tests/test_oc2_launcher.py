import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Oc2LauncherTests(unittest.TestCase):
    def _make_toolkit(self, tmp_path: Path):
        toolkit = tmp_path / "toolkit"
        scripts = toolkit / "scripts"
        scripts.mkdir(parents=True)

        shutil.copy2(ROOT / "scripts" / "opencode-agents", scripts / "opencode-agents")

        for name in ("generate-config", "apply-reliability", "resolve-models"):
            path = scripts / name
            path.write_text("#!/usr/bin/env python3\n")
            path.chmod(0o755)

        (toolkit / ".env").write_text(
            "OPENCODE_MAJOR=1\n"
            "OPENCODE_PREFLIGHT=0\n"
        )

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        for binary in ("opencode", "opencode2"):
            path = bin_dir / binary
            path.write_text(
                "#!/usr/bin/env bash\n"
                f"echo 'binary={binary}'\n"
                "echo \"major=${OPENCODE_MAJOR:-}\"\n"
                "echo \"config=${OPENCODE_CONFIG:-}\"\n"
                "echo \"args=$*\"\n"
            )
            path.chmod(0o755)

        return toolkit, bin_dir

    def test_oc2_symlink_forces_v2_even_when_env_defaults_to_v1(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            toolkit, bin_dir = self._make_toolkit(tmp_path)
            launcher = bin_dir / "oc2"
            launcher.symlink_to(toolkit / "scripts" / "opencode-agents")

            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            env.pop("OPENCODE_MAJOR", None)
            env.pop("OPENCODE_BIN", None)

            result = subprocess.run(
                [str(launcher), "run", "hello"],
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("binary=opencode2", result.stdout)
            self.assertIn("major=2", result.stdout)
            self.assertIn(f"config={toolkit / 'opencode.v2.jsonc'}", result.stdout)
            self.assertIn("args=run hello", result.stdout)

    def test_explicit_v2_override_wins_over_env_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            toolkit, bin_dir = self._make_toolkit(tmp_path)

            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            env["OPENCODE_MAJOR"] = "2"
            env.pop("OPENCODE_BIN", None)

            result = subprocess.run(
                ["bash", str(toolkit / "scripts" / "opencode-agents"), "run", "hello"],
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("binary=opencode2", result.stdout)
            self.assertIn("major=2", result.stdout)
            self.assertIn(f"config={toolkit / 'opencode.v2.jsonc'}", result.stdout)


if __name__ == "__main__":
    unittest.main()
