import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from runtime.common.adapter import ArtifactPlan

ROOT = Path(__file__).resolve().parents[1]


def filesystem_snapshot(root):
    """Include directories, bytecode, file bytes and mtimes; reads do not count as writes."""
    result = {}
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        stat = path.lstat()
        if path.is_symlink():
            result[relative] = ("symlink", os.readlink(path), stat.st_mtime_ns)
        elif path.is_dir():
            result[relative] = ("directory", stat.st_mtime_ns)
        else:
            result[relative] = ("file", path.read_bytes(), stat.st_mtime_ns)
    return result


class RuntimeSyncTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for directory in ("agents", "runtime"):
            shutil.copytree(ROOT / directory, self.root / directory, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        scripts = self.root / "scripts"
        scripts.mkdir()
        for filename in ("opencode-agents", "sync-runtime", "generate-config", "agent_config.py", "apply-reliability"):
            shutil.copy2(ROOT / "scripts" / filename, scripts / filename)
        shutil.copy2(ROOT / "reliability.json", self.root / "reliability.json")
        self.launcher = self.root / "bin" / "oc"
        self.launcher.parent.mkdir()
        self.launcher.symlink_to(scripts / "opencode-agents")
        self.env = {key: value for key, value in os.environ.items() if not key.startswith(("CODEX_MODEL_", "CODEX_REASONING_", "PYTHON"))}
        self.env["OAT_RUNTIME"] = "docker"

    def sync(self, *args, launcher=True, extra_env=None, cwd=None):
        command = ["bash", str(self.launcher), "sync"] if launcher else [sys.executable, "-B", str(self.root / "scripts" / "sync-runtime")]
        return subprocess.run(command + list(args), cwd=cwd or self.root, env={**self.env, **(extra_env or {})}, capture_output=True, text=True)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_first_oc_dry_run_has_zero_filesystem_mutation_including_bytecode(self):
        before = filesystem_snapshot(self.root)
        result = self.sync("codex", "--dry-run", extra_env={"CODEX_MODEL_LOW": "configured-low"})
        self.assert_success(result)
        self.assertEqual(filesystem_snapshot(self.root), before)
        self.assertIn("CREATE", result.stdout)
        self.assertIn("AGENTS.md", result.stdout)
        self.assertIn("configured-low", result.stdout)
        self.assertFalse((self.root / ".generated").exists())

    def test_oc_sync_works_without_env_provider_or_docker_setup(self):
        self.assertFalse((self.root / ".env").exists())
        result = self.sync("codex")
        self.assert_success(result)
        self.assertTrue((self.root / ".generated" / "codex" / "AGENTS.md").is_file())
        self.assertFalse((self.root / "opencode.jsonc").exists())

    def test_symlinked_oc_resolves_toolkit_from_an_unrelated_project(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "AGENTS.md").write_text("User project instructions\n")
            before = filesystem_snapshot(project)
            self.assert_success(self.sync("codex", cwd=project))
            self.assertTrue((self.root / ".generated" / "codex" / "AGENTS.md").is_file())
            self.assertEqual(filesystem_snapshot(project), before)

    def test_sync_does_not_source_shell_profile_files(self):
        for filename in (".env", ".env.local"):
            (self.root / filename).write_text("exit 89\n")
        self.assert_success(self.sync("codex", "--dry-run"))

    def test_check_missing_artifacts_fails_without_writing(self):
        before = filesystem_snapshot(self.root)
        result = self.sync("codex", "--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(filesystem_snapshot(self.root), before)

    def test_check_passes_when_synced_and_fails_for_content_or_missing_file(self):
        self.assert_success(self.sync("codex"))
        before = filesystem_snapshot(self.root)
        self.assert_success(self.sync("codex", "--check"))
        self.assertEqual(filesystem_snapshot(self.root), before)
        instructions = self.root / ".generated" / "codex" / "AGENTS.md"
        instructions.write_text("drift\n")
        before = filesystem_snapshot(self.root)
        result = self.sync("codex", "--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("AGENTS.md", result.stdout)
        self.assertEqual(filesystem_snapshot(self.root), before)
        instructions.unlink()
        before = filesystem_snapshot(self.root)
        self.assertNotEqual(self.sync("codex", "--check").returncode, 0)
        self.assertEqual(filesystem_snapshot(self.root), before)

    def test_dry_run_reports_updates_without_repair(self):
        self.assert_success(self.sync("codex"))
        instructions = self.root / ".generated" / "codex" / "AGENTS.md"
        instructions.write_text("local drift\n")
        before = filesystem_snapshot(self.root)
        result = self.sync("codex", "--dry-run")
        self.assert_success(result)
        self.assertIn("UPDATE", result.stdout)
        self.assertEqual(filesystem_snapshot(self.root), before)

    def test_sync_all_is_idempotent_and_checkable(self):
        self.assert_success(self.sync("all"))
        first = filesystem_snapshot(self.root)
        self.assert_success(self.sync("all"))
        self.assertEqual(filesystem_snapshot(self.root), first)
        self.assert_success(self.sync("all", "--check"))
        self.assertTrue((self.root / "opencode.jsonc").is_file())
        self.assertTrue((self.root / ".generated" / "codex" / "runtime.json").is_file())

    def test_opencode_sync_matches_existing_generation_and_current_golden(self):
        self.assert_success(self.sync("opencode"))
        paths = [self.root / "opencode.jsonc", self.root / "opencode.v2.jsonc", self.root / ".generated" / "agents.json"]
        paths += sorted((self.root / ".generated" / "prompts").glob("*.md"))
        actual = {str(p.relative_to(self.root)): p.read_bytes() for p in paths}
        result = subprocess.run([sys.executable, "-B", str(self.root / "scripts" / "generate-config")], cwd=self.root, env=self.env, capture_output=True, text=True)
        self.assert_success(result)
        self.assertEqual(actual, {str(p.relative_to(self.root)): p.read_bytes() for p in paths})
        result = subprocess.run([sys.executable, "-B", str(self.root / "scripts" / "apply-reliability")], cwd=self.root, env=self.env, capture_output=True, text=True)
        self.assert_success(result)
        from test_config_parity import generated_output_digests
        golden = json.loads((ROOT / "tests" / "fixtures" / "opencode-output.sha256.json").read_text())
        self.assertEqual(generated_output_digests(self.root), golden)

    def test_unknown_runtime_and_conflicting_flags_fail_without_writes(self):
        before = filesystem_snapshot(self.root)
        for args in (("unsupported",), ("codex", "--check", "--dry-run")):
            self.assertNotEqual(self.sync(*args).returncode, 0)
            self.assertEqual(filesystem_snapshot(self.root), before)

    def test_invalid_codex_policy_prevents_partial_all_generation(self):
        before = filesystem_snapshot(self.root)
        result = self.sync("all", extra_env={"CODEX_REASONING_BUILDER": "invalid"})
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(filesystem_snapshot(self.root), before)

    def test_non_directory_codex_output_ancestor_prevents_partial_all_generation(self):
        (self.root / ".generated").mkdir()
        (self.root / ".generated" / "codex").write_text("not a directory\n")
        before = filesystem_snapshot(self.root)
        self.assertNotEqual(self.sync("all").returncode, 0)
        self.assertEqual(filesystem_snapshot(self.root), before)

    def test_stale_agent_outputs_are_detected_and_removed_but_unowned_files_survive(self):
        self.assert_success(self.sync("codex"))
        agents = self.root / ".generated" / "codex" / "agents"
        stale = agents / "removed-agent.md"
        stale.write_text("<!-- GENERATED BY opencode-agent-toolkit. DO NOT EDIT DIRECTLY. -->\n")
        user_agent_note = agents / "notes.md"
        user_agent_note.write_text("User notes, not generated\n")
        preserved = self.root / ".generated" / "codex" / "local-notes.txt"
        preserved.write_text("not generated\n")
        before = filesystem_snapshot(self.root)
        self.assertNotEqual(self.sync("codex", "--check").returncode, 0)
        self.assertEqual(filesystem_snapshot(self.root), before)
        self.assert_success(self.sync("codex"))
        self.assertFalse(stale.exists())
        self.assertEqual(user_agent_note.read_text(), "User notes, not generated\n")
        self.assertEqual(preserved.read_text(), "not generated\n")

    def test_generated_symlink_ancestor_is_rejected_without_external_writes(self):
        with tempfile.TemporaryDirectory() as external_directory:
            external = Path(external_directory)
            (self.root / ".generated").symlink_to(external, target_is_directory=True)
            before = filesystem_snapshot(self.root)
            self.assertNotEqual(self.sync("codex").returncode, 0)
            self.assertEqual(list(external.iterdir()), [])
            self.assertEqual(filesystem_snapshot(self.root), before)


class ArtifactPlanTests(unittest.TestCase):
    def test_create_update_delete_and_write_use_shared_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            changed = root / "changed.txt"
            changed.write_bytes(b"old")
            stale = root / "stale.txt"
            stale.write_bytes(b"stale")
            created = root / "nested" / "created.txt"
            plan = ArtifactPlan(root, {created: b"new", changed: b"updated"}, stale=(stale,))
            self.assertEqual(plan.changes(), {created: "CREATE", changed: "UPDATE", stale: "DELETE"})
            plan.write()
            self.assertEqual(created.read_bytes(), b"new")
            self.assertEqual(changed.read_bytes(), b"updated")
            self.assertFalse(stale.exists())
            self.assertEqual(plan.changes(), {})

    def test_outside_root_target_is_rejected_before_any_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                ArtifactPlan(root, {root.parent / "outside.txt": b"no"}).write()
            self.assertEqual(list(root.iterdir()), [])

    def test_non_directory_ancestor_is_rejected_before_any_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            blocker = root / "z-blocker"
            blocker.write_bytes(b"not a directory")
            before = filesystem_snapshot(root)
            plan = ArtifactPlan(root, {root / "a-first.txt": b"must not write", blocker / "child.txt": b"no"})
            with self.assertRaises(ValueError):
                plan.write()
            self.assertEqual(filesystem_snapshot(root), before)


if __name__ == "__main__":
    unittest.main()
