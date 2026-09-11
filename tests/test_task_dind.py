"""Exercise managed DinD startup without needing a Docker daemon or credentials."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TaskDinDTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.calls = self.directory / "calls.jsonl"
        docker = self.directory / "docker"
        docker.write_text(
            f"#!{sys.executable}\n" + '''import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with open(os.environ["FAKE_DOCKER_CALLS"], "a") as output:
    output.write(json.dumps(args) + "\\n")
mode = os.environ.get("FAKE_DOCKER_MODE", "ready")
if args[:2] == ["run", "-d"]:
    if mode == "start-failure":
        print("daemon creation refused", file=sys.stderr)
        sys.exit(125)
    print("fake-dind-id")
elif args[0] == "inspect":
    print("false" if mode == "exited" else "true")
elif args[0] == "logs":
    print("rootlesskit: fork/exec /proc/self/exe: operation not permitted")
elif args[:2] == ["run", "--rm"]:
    if mode == "timeout":
        print("cannot connect to rootless API", file=sys.stderr)
        sys.exit(1)
    if mode == "transient":
        marker = Path(os.environ["FAKE_DOCKER_CALLS"] + ".first")
        if not marker.exists():
            marker.touch()
            sys.exit(1)
    print(json.dumps(["name=seccomp"] if mode == "rootful" else ["name=rootless"]))
else:
    raise SystemExit("unexpected Docker command: " + repr(args))
'''
        )
        docker.chmod(0o755)
        self.env = os.environ.copy()
        self.env.pop("OAT_TASK_DIND_APPARMOR_PROFILE", None)
        self.env.update({
            "PATH": str(self.directory) + os.pathsep + self.env.get("PATH", ""),
            "FAKE_DOCKER_CALLS": str(self.calls),
            "OAT_TASK_DIND_WAIT_SECONDS": "5",
            "OAT_GITHUB_TOKEN": "must-not-be-forwarded",
        })
        self.args = ["oat-dind-test", "oat-network-test", "workspace-test", "data-test",
                     "docker:29-dind-rootless", "opencode-agent-toolkit:ci"]

    def invoke(self, mode="ready", **overrides):
        env = {**self.env, "FAKE_DOCKER_MODE": mode, **overrides}
        result = subprocess.run(
            ["bash", str(ROOT / "scripts" / "task-dind"), *self.args],
            env=env, capture_output=True, text=True, timeout=10,
        )
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()] if self.calls.exists() else []
        return result, calls

    def test_startup_keeps_rootless_named_volumes_and_no_host_exposure(self):
        result, calls = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        start = calls[0]
        self.assertIn("--privileged", start)
        self.assertEqual(start[-1], "docker:29-dind-rootless")
        self.assertIn("DOCKER_TLS_CERTDIR=", start)
        mounts = [start[i + 1] for i, arg in enumerate(start) if arg == "--mount"]
        self.assertEqual(mounts, [
            "type=volume,src=workspace-test,dst=/workspace",
            "type=volume,src=data-test,dst=/home/rootless/.local/share/docker",
        ])
        for forbidden in ("-p", "--publish", "--publish-all", "--security-opt"):
            self.assertNotIn(forbidden, start)
        rendered = json.dumps(calls)
        self.assertNotIn("DOCKERD_ROOTLESS_ROOTLESSKIT_FLAGS=", rendered)
        self.assertNotIn("/var/run/docker.sock", rendered)
        self.assertNotIn("GITHUB_TOKEN", rendered)
        self.assertNotIn("must-not-be-forwarded", rendered)

    def test_checks_worker_tcp_endpoint_not_outer_exec_unix_socket(self):
        result, calls = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        probes = [call for call in calls if call[:2] == ["run", "--rm"]]
        self.assertEqual(len(probes), 1)
        self.assertIn("DOCKER_HOST=tcp://docker-agent:2375", probes[0])
        self.assertIn("timeout", probes[0])
        self.assertIn("5s", probes[0])
        self.assertIn("{{json .SecurityOptions}}", probes[0])
        self.assertFalse(any(call[0] == "exec" for call in calls))

    def test_optional_apparmor_profile_is_scoped_to_daemon(self):
        result, calls = self.invoke(OAT_TASK_DIND_APPARMOR_PROFILE="oat-dind-rootless")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("apparmor=oat-dind-rootless", calls[0])
        self.assertNotIn("--security-opt", calls[-1])

    def test_refuses_non_rootless_daemon_without_fallback(self):
        result, calls = self.invoke("rootful")
        self.assertEqual(result.returncode, 3)
        self.assertIn("not rootless", result.stderr)
        self.assertEqual(sum(call[:2] == ["run", "-d"] for call in calls), 1)

    def test_exited_daemon_reports_logs_and_returns_error(self):
        result, calls = self.invoke("exited")
        self.assertEqual(result.returncode, 3)
        self.assertIn("operation not permitted", result.stderr)
        self.assertIn("AppArmor", result.stderr)
        self.assertFalse(any(call[:2] == ["run", "--rm"] for call in calls))

    def test_unreachable_endpoint_times_out_with_last_error(self):
        result, _ = self.invoke("timeout", OAT_TASK_DIND_WAIT_SECONDS="1")
        self.assertEqual(result.returncode, 3)
        self.assertIn("timed out", result.stderr)
        self.assertIn("cannot connect", result.stderr)

    def test_transient_startup_failure_can_recover(self):
        result, calls = self.invoke("transient")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sum(call[:2] == ["run", "--rm"] for call in calls), 2)

    def test_docker_create_failure_is_not_hidden(self):
        result, calls = self.invoke("start-failure")
        self.assertEqual(result.returncode, 125)
        self.assertEqual(len(calls), 1)

    def test_invalid_profile_is_rejected_before_docker(self):
        result, calls = self.invoke(OAT_TASK_DIND_APPARMOR_PROFILE="bad,profile")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(calls, [])

    def test_invalid_volume_name_is_rejected_before_docker(self):
        self.args[2] = "workspace,dst=/host"
        result, calls = self.invoke()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(calls, [])

    def test_invalid_wait_is_rejected_before_docker(self):
        for value in ("0", "601", "01", "bad"):
            with self.subTest(value=value):
                result, calls = self.invoke(OAT_TASK_DIND_WAIT_SECONDS=value)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(calls, [])

    def test_ci_and_task_share_startup_and_do_not_disable_global_policy(self):
        task = (ROOT / "scripts" / "task-run").read_text()
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
        helper = (ROOT / "scripts" / "task-dind").read_text()
        self.assertIn('bash "$ROOT/scripts/task-dind"', task)
        self.assertIn("bash scripts/task-dind", workflow)
        self.assertIn("apparmor_parser -r runtime/apparmor/oat-dind-rootless", workflow)
        self.assertIn("apparmor_parser -R runtime/apparmor/oat-dind-rootless", workflow)
        self.assertIn("OAT_TASK_DIND_APPARMOR_PROFILE=oat-dind-rootless", workflow)
        self.assertIn("/workspace/.dind-smoke", workflow)
        self.assertNotIn("DOCKERD_ROOTLESS_ROOTLESSKIT_FLAGS=", task)
        for text in (task, workflow, helper):
            self.assertNotIn("sysctl -w", text)
            self.assertNotIn("apparmor_restrict_unprivileged_userns=0", text)
        self.assertNotIn("apparmor_parser", helper)
        self.assertNotIn("sudo ", helper)
        self.assertIn("userns,", (ROOT / "runtime" / "apparmor" / "oat-dind-rootless").read_text())

    def test_helper_and_launcher_shell_syntax(self):
        for name in ("task-dind", "task-run"):
            result = subprocess.run(["bash", "-n", str(ROOT / "scripts" / name)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
