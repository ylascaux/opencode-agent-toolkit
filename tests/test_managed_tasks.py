import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ManagedTaskIsolationTests(unittest.TestCase):
    def test_shell_scripts_are_syntactically_valid(self):
        for name in ["task-run", "workspace-broker", "docker-runtime", "opencode-agents"]:
            result = subprocess.run(
                ["bash", "-n", str(ROOT / "scripts" / name)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, f"{name}: {result.stderr}")

    def test_normal_runtime_uses_dind_not_host_socket(self):
        compose = (ROOT / "compose.yaml").read_text()
        runtime = (ROOT / "scripts" / "docker-runtime").read_text()
        self.assertIn("docker-agent:", compose)
        self.assertIn("OAT_DIND_IMAGE", compose)
        self.assertIn("DOCKER_HOST: tcp://docker-agent:2375", compose)
        self.assertNotIn("/var/run/docker.sock", compose)
        self.assertNotIn("OAT_DOCKER_SOCKET", compose)
        self.assertNotIn("OAT_DOCKER_SOCKET", runtime)

    def test_docker_runtime_preserves_explicit_major_across_env_loading(self):
        runtime = (ROOT / "scripts" / "docker-runtime").read_text()
        requested = runtime.index('REQUESTED_MAJOR="${OPENCODE_MAJOR:-}"')
        source_env = runtime.index('source "$ROOT/.env"')
        restore = runtime.index('OPENCODE_MAJOR="$REQUESTED_MAJOR"')
        major_select = runtime.index('major="${OPENCODE_MAJOR:-1}"')
        self.assertLess(requested, source_env)
        self.assertLess(source_env, restore)
        self.assertLess(restore, major_select)
        self.assertIn("export OPENCODE_MAJOR", runtime[restore:major_select])

    def test_oc2_browser_oauth_callback_is_not_exposed(self):
        compose = (ROOT / "compose.yaml").read_text()
        self.assertIn('127.0.0.1:${OAT_OC2_PORT:-4096}:4096', compose)
        self.assertNotIn("OAT_OC2_OAUTH_PORT", compose)
        self.assertNotIn(":1455", compose)

    def test_managed_task_requires_explicit_approval_and_rootless_dind(self):
        script = (ROOT / "scripts" / "task-run").read_text()
        self.assertIn("Managed execution requires explicit --approved", script)
        self.assertIn("docker:29-dind-rootless", script)
        self.assertIn("DOCKER_HOST=tcp://docker-agent:2375", script)
        self.assertIn("PLAN_APPROVAL_MODE=off", script)
        self.assertIn("[MANAGED_TASK_ROOT_APPROVED]", script)
        self.assertNotIn("/var/run/docker.sock", script)

    def test_github_credential_is_not_injected_into_worker_block(self):
        script = (ROOT / "scripts" / "task-run").read_text()
        worker = script.split("# No GitHub token", 1)[1].split("worker_status=$?", 1)[0]
        self.assertNotIn("OAT_GITHUB_TOKEN", worker)
        self.assertNotIn("GITHUB_TOKEN", worker)
        self.assertIn('-e OAT_GITHUB_TOKEN="$token"', script)

    def test_workspace_broker_only_publishes_generated_agent_branch(self):
        broker = (ROOT / "scripts" / "workspace-broker").read_text()
        self.assertIn('[[ "$branch" =~ ^agent/', broker)
        self.assertIn("refusing protected/base branch", broker)
        self.assertIn('push origin "HEAD:refs/heads/$branch"', broker)
        self.assertNotIn("push --force", broker)
        self.assertNotIn("push -f", broker)

    def test_orchestrator_knows_broker_owns_publication(self):
        prompt = (ROOT / "agents" / "orchestrator" / "prompt.md").read_text()
        self.assertIn("[MANAGED_TASK_ROOT_APPROVED]", prompt)
        self.assertIn("trusted workspace broker", prompt)
        self.assertIn("Do not claim a PR number or URL", prompt)

    def test_memory_broker_imports_only_valid_candidate_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_state = root / "task"
            host_state = root / "host"
            candidates = task_state / "memory" / "candidates"
            candidates.mkdir(parents=True)
            fingerprint = "a" * 64
            payload = {
                "id": fingerprint[:12],
                "fingerprint": fingerprint,
                "kind": "decision",
                "confidence": "high",
                "title": "Use isolated workspaces",
                "statement": "Managed tasks use ephemeral workspaces.",
                "project_id": "demo",
                "occurrences": 1,
            }
            (candidates / f"{fingerprint}.json").write_text(json.dumps(payload))

            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "memory-broker"),
                    "collect",
                    str(task_state),
                    str(host_state),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            imported = host_state / "memory" / "candidates" / f"{fingerprint}.json"
            self.assertTrue(imported.is_file())
            self.assertEqual(json.loads(imported.read_text())["fingerprint"], fingerprint)

    def test_memory_broker_rejects_symlink_candidate(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unsupported")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_state = root / "task"
            host_state = root / "host"
            candidates = task_state / "memory" / "candidates"
            candidates.mkdir(parents=True)
            fingerprint = "b" * 64
            outside = root / "outside.json"
            outside.write_text("{}")
            try:
                os.symlink(outside, candidates / f"{fingerprint}.json")
            except OSError:
                self.skipTest("symlink creation unsupported")

            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "memory-broker"),
                    "collect",
                    str(task_state),
                    str(host_state),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refusing non-regular candidate", result.stderr)


if __name__ == "__main__":
    unittest.main()
