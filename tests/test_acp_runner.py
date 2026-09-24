import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from runtime.common.acp import AcpRunner, default_runner, load_runners

ROOT = Path(__file__).resolve().parents[1]


class AcpRunnerTests(unittest.TestCase):
    def test_builtin_opencode_runner_uses_native_acp(self):
        runner = load_runners()["opencode"]
        self.assertEqual(runner.command, "opencode")
        self.assertEqual(runner.args, ("acp",))
        self.assertTrue(runner.enabled)
        self.assertTrue(runner.trusted)

    def test_opencode_binary_override_is_used_without_changing_registry(self):
        runner = load_runners()["opencode"]
        self.assertEqual(runner.argv({"OPENCODE_BIN": "/tmp/custom-opencode"}), ["/tmp/custom-opencode", "acp"])

    def test_default_runner_is_explicit_and_rejects_unknown(self):
        runners = {"opencode": AcpRunner("opencode", "opencode", ("acp",))}
        self.assertEqual(default_runner(runners, {}).id, "opencode")
        with self.assertRaises(ValueError):
            default_runner(runners, {"OAT_ACP_DEFAULT_RUNNER": "missing"})

    def test_untrusted_runner_metadata_remains_explicit(self):
        runner = AcpRunner("external", "external-agent", ("acp",), trusted=False)
        self.assertFalse(runner.trusted)

    def test_runner_cli_command_is_machine_readable(self):
        result = subprocess.run(
            ["python3", str(ROOT / "scripts" / "acp-runner"), "command", "opencode", "--json"],
            env={**os.environ, "OPENCODE_BIN": "/fixture/opencode"},
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"runner": "opencode", "argv": ["/fixture/opencode", "acp"]})


if __name__ == "__main__":
    unittest.main()
