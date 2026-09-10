from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MemoryCliRoutingTests(unittest.TestCase):
    def test_oc_memory_preserves_caller_working_directory_and_skips_opencode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            toolkit = tmp_path / "toolkit"
            scripts = toolkit / "scripts"
            scripts.mkdir(parents=True)
            shutil.copy2(ROOT / "scripts" / "opencode-agents", scripts / "opencode-agents")

            (toolkit / ".env").write_text("OPENCODE_MAJOR=1\n")
            memory = scripts / "memory"
            memory.write_text(
                "#!/usr/bin/env python3\n"
                "import os, sys\n"
                "print(f'cwd={os.getcwd()}')\n"
                "print('args=' + ' '.join(sys.argv[1:]))\n"
            )
            memory.chmod(0o755)

            project = tmp_path / "project"
            project.mkdir()
            env = os.environ.copy()
            env["OPENCODE_BIN"] = str(tmp_path / "must-not-run")

            result = subprocess.run(
                ["bash", str(scripts / "opencode-agents"), "memory", "status"],
                cwd=project,
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            output = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
            self.assertEqual(Path(output["cwd"]).resolve(), project.resolve())
            self.assertEqual(output["args"], "status")

    def test_oc_memory_without_subcommand_shows_memory_help(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            toolkit = tmp_path / "toolkit"
            scripts = toolkit / "scripts"
            scripts.mkdir(parents=True)
            shutil.copy2(ROOT / "scripts" / "opencode-agents", scripts / "opencode-agents")
            (toolkit / ".env").write_text("OPENCODE_MAJOR=1\n")
            memory = scripts / "memory"
            memory.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "print('args=' + ' '.join(sys.argv[1:]))\n"
            )
            memory.chmod(0o755)

            result = subprocess.run(
                ["bash", str(scripts / "opencode-agents"), "memory"],
                cwd=tmp_path,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("args=--help", result.stdout)


if __name__ == "__main__":
    unittest.main()
