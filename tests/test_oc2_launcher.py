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
            "OAT_SANDBOX_ENABLED=0\n"
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
                "echo \"server_username=${OPENCODE_SERVER_USERNAME:-}\"\n"
                "if [[ -n \"${OPENCODE_SERVER_PASSWORD:-}\" ]]; then echo 'server_password_set=1'; else echo 'server_password_set=0'; fi\n"
                "echo \"args=$*\"\n"
            )
            path.chmod(0o755)

        return toolkit, bin_dir

    @staticmethod
    def _output_map(stdout: str) -> dict[str, str]:
        return {
            key: value
            for line in stdout.splitlines()
            if "=" in line
            for key, value in [line.split("=", 1)]
        }

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
            output = self._output_map(result.stdout)
            self.assertEqual(output["binary"], "opencode2")
            self.assertEqual(output["major"], "2")
            self.assertEqual(
                Path(output["config"]).resolve(),
                (toolkit / "opencode.v2.jsonc").resolve(),
            )
            self.assertEqual(output["args"], "run hello")

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
            output = self._output_map(result.stdout)
            self.assertEqual(output["binary"], "opencode2")
            self.assertEqual(output["major"], "2")
            self.assertEqual(
                Path(output["config"]).resolve(),
                (toolkit / "opencode.v2.jsonc").resolve(),
            )

    def test_oc2_web_maps_to_v2_serve_and_forwards_auth(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            toolkit, bin_dir = self._make_toolkit(tmp_path)
            launcher = bin_dir / "oc2"
            launcher.symlink_to(toolkit / "scripts" / "opencode-agents")

            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            env["OPENCODE_SERVER_USERNAME"] = "toolkit-user"
            env["OPENCODE_SERVER_PASSWORD"] = "test-secret"
            env.pop("OPENCODE_MAJOR", None)
            env.pop("OPENCODE_BIN", None)

            result = subprocess.run(
                [str(launcher), "web", "--port", "4096", "--hostname", "127.0.0.1"],
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            output = self._output_map(result.stdout)
            self.assertEqual(output["binary"], "opencode2")
            self.assertEqual(output["major"], "2")
            self.assertEqual(
                Path(output["config"]).resolve(),
                (toolkit / "opencode.v2.jsonc").resolve(),
            )
            self.assertEqual(output["server_username"], "toolkit-user")
            self.assertEqual(output["server_password_set"], "1")
            self.assertEqual(
                output["args"],
                "serve --port 4096 --hostname 127.0.0.1",
            )
            self.assertNotIn("test-secret", result.stdout)
            self.assertIn("'web' is mapped to 'serve'", result.stderr)


if __name__ == "__main__":
    unittest.main()
