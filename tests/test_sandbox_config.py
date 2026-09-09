import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SandboxConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            ["python3", str(ROOT / "scripts" / "generate-config")],
            check=True,
            capture_output=True,
            text=True,
        )
        cls.v1 = json.loads((ROOT / "opencode.jsonc").read_text())
        cls.v2 = json.loads((ROOT / "opencode.v2.jsonc").read_text())

    def test_sandbox_routing_is_generated_for_both_runtimes(self):
        self.assertIn("./runtime/plugins/sandbox-v1.js", self.v1["plugin"])
        self.assertEqual(
            Path(self.v2["shell"]).resolve(),
            (ROOT / "scripts" / "sandbox-shell-v2").resolve(),
        )
        # V2 must not rely on a session-local plugin hook: the global shell is inherited
        # by child sessions/subagents and is therefore the actual sandbox boundary.
        self.assertNotIn("./runtime/plugins/sandbox-v2.ts", self.v2["plugins"])

    def test_v2_global_shell_is_fail_closed_when_sandboxed(self):
        wrapper = ROOT / "scripts" / "sandbox-shell-v2"
        self.assertTrue(wrapper.is_file())
        self.assertTrue(wrapper.stat().st_mode & 0o111)
        text = wrapper.read_text()
        self.assertIn("OAT_SANDBOX_CONTAINER is not set", text)
        self.assertIn("OAT_SANDBOX_PROJECT_ROOT is not set", text)
        self.assertIn('exec bash "$ROOT/scripts/sandbox-run"', text)
        self.assertIn("refusing unsupported shell invocation while sandboxed", text)

    def test_runtime_internals_are_outside_v2_auto_discovery_directory(self):
        self.assertFalse((ROOT / ".opencode" / "plugins").exists())
        runtime = ROOT / "runtime" / "plugins"
        for filename in [
            "sandbox-v1.js", "sandbox-v2.ts", "plan-approval-core.js",
            "plan-approval-v1.js", "plan-approval-v2.ts", "reliability-core.js",
            "reliability-v1.js", "reliability-v2.ts",
        ]:
            self.assertTrue((runtime / filename).is_file(), filename)

    def test_aws_and_kubectl_are_manual_only(self):
        permissions = json.loads((ROOT / "agents" / "_defaults" / "permissions.json").read_text())
        bash = permissions["bash"]
        self.assertEqual(bash["aws *"], "deny")
        self.assertEqual(bash["kubectl *"], "deny")
        prompt = (ROOT / "agents" / "_defaults" / "prompt.md").read_text()
        self.assertIn("NEVER execute `aws ...` or `kubectl ...` commands", prompt)
        self.assertIn("ask them to paste the output back", prompt)

    def test_remote_git_and_ssh_are_manual_only(self):
        permissions = json.loads((ROOT / "agents" / "_defaults" / "permissions.json").read_text())
        bash = permissions["bash"]
        for command in [
            "git fetch*", "git pull*", "git push*", "git clone*", "git ls-remote*",
            "git remote update*", "git submodule update*", "git archive --remote*",
            "ssh *", "scp *", "sftp *",
        ]:
            self.assertEqual(bash[command], "deny", command)
        prompt = (ROOT / "agents" / "_defaults" / "prompt.md").read_text()
        self.assertIn("Remote Git access is manual-only", prompt)
        self.assertIn("The sandbox never receives the host SSH private keys or `SSH_AUTH_SOCK`", prompt)
        policy = json.loads((ROOT / "sandbox" / "policy.json").read_text())
        self.assertEqual(policy["source_control"]["remote_mode"], "manual_only")
        self.assertFalse(policy["source_control"]["agent_remote_execution"])
        self.assertFalse(policy["source_control"]["ssh_credentials_mounted"])
        self.assertFalse(policy["source_control"]["ssh_agent_forwarded"])

    def test_native_reads_of_host_credentials_are_denied(self):
        permissions = json.loads((ROOT / "agents" / "_defaults" / "permissions.json").read_text())
        reads = permissions["read"]
        for pattern in [
            "**/.ssh/**", "**/.aws/**", "**/.kube/**", "**/.azure/**",
            "**/.config/gcloud/**", "**/.config/gh/**",
        ]:
            self.assertEqual(reads[pattern], "deny", pattern)

    def test_cloud_mutations_remain_denied_defense_in_depth(self):
        permissions = json.loads((ROOT / "agents" / "_defaults" / "permissions.json").read_text())
        bash = permissions["bash"]
        for command in ["kubectl apply*", "kubectl delete*", "helm upgrade*", "aws * delete*", "aws * terminate*"]:
            self.assertEqual(bash[command], "deny", command)

    def test_policy_never_mounts_host_credentials_or_docker_socket(self):
        policy = json.loads((ROOT / "sandbox" / "policy.json").read_text())
        denied = set(policy["filesystem"]["never_mount"])
        for value in ["~/.aws", "~/.ssh", "~/.kube", "~/.config/gh", "/var/run/docker.sock", "$SSH_AUTH_SOCK"]:
            self.assertIn(value, denied)
        self.assertEqual(policy["cloud"]["mode"], "manual_only")
        self.assertFalse(policy["cloud"]["agent_execution"])

    def test_base_image_does_not_install_cloud_clis(self):
        dockerfile = (ROOT / "sandbox" / "Dockerfile").read_text()
        tools = (ROOT / "sandbox" / "tools.nix").read_text()
        self.assertNotIn("awscli", dockerfile + tools)
        self.assertNotIn("kubectl", dockerfile + tools)

    def test_runtime_hardening_is_present(self):
        launcher = (ROOT / "scripts" / "sandbox-start").read_text()
        self.assertIn("--cap-drop=ALL", launcher)
        self.assertIn("--security-opt=no-new-privileges", launcher)
        self.assertNotIn("/var/run/docker.sock:/var/run/docker.sock", launcher)
        self.assertNotIn("SSH_AUTH_SOCK", launcher)
        self.assertNotIn("/.ssh:", launcher)

    def test_sandbox_runner_has_no_host_cloud_execution_path(self):
        runner = (ROOT / "scripts" / "sandbox-run").read_text()
        self.assertNotIn("cloud-broker", runner)
        self.assertNotIn("cloud_policy", runner)
        launcher = (ROOT / "scripts" / "opencode-agents").read_text()
        self.assertNotIn("OAT_CLOUD_BROKER_ENABLED", launcher)


if __name__ == "__main__":
    unittest.main()
