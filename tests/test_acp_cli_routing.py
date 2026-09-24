from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AcpCliRoutingTests(unittest.TestCase):
    def test_oc_runner_is_local_and_preserves_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            toolkit = base / "toolkit"
            scripts = toolkit / "scripts"
            scripts.mkdir(parents=True)
            shutil.copy2(ROOT / "scripts" / "opencode-agents", scripts / "opencode-agents")
            (toolkit / ".env").write_text("OAT_RUNTIME=host\n")

            runner = scripts / "acp-runner"
            runner.write_text(
                "#!/usr/bin/env python3\n"
                "import os, sys\n"
                "print(f'cwd={os.getcwd()}')\n"
                "print('args=' + ' '.join(sys.argv[1:]))\n"
            )
            runner.chmod(0o755)

            project = base / "project"
            project.mkdir()
            env = os.environ.copy()
            env["OPENCODE_BIN"] = str(base / "must-not-run")

            result = subprocess.run(
                ["bash", str(scripts / "opencode-agents"), "runner", "doctor", "opencode"],
                cwd=project,
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            output = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
            self.assertEqual(Path(output["cwd"]).resolve(), project.resolve())
            self.assertEqual(output["args"], "doctor opencode")

    def test_oc_runner_without_subcommand_lists_runners(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            toolkit = base / "toolkit"
            scripts = toolkit / "scripts"
            scripts.mkdir(parents=True)
            shutil.copy2(ROOT / "scripts" / "opencode-agents", scripts / "opencode-agents")
            (toolkit / ".env").write_text("OAT_RUNTIME=host\n")
            runner = scripts / "acp-runner"
            runner.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "print('args=' + ' '.join(sys.argv[1:]))\n"
            )
            runner.chmod(0o755)

            result = subprocess.run(
                ["bash", str(scripts / "opencode-agents"), "runner"],
                cwd=base,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("args=list", result.stdout)


if __name__ == "__main__":
    unittest.main()
