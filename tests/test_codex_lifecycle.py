import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.codex import lifecycle


def snapshot(root):
    return {
        str(path.relative_to(root)): ("symlink", os.readlink(path)) if path.is_symlink()
        else ("dir",) if path.is_dir() else ("file", path.read_bytes())
        for path in sorted(root.rglob("*"))
    }


class CodexLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / "toolkit"
        self.project = Path(self.directory.name) / "project"
        (self.root / ".generated" / "codex" / "agents").mkdir(parents=True)
        (self.root / ".generated" / "codex" / "agents" / "builder.toml").write_text('name = "builder"\n')
        (self.root / "scripts").mkdir()
        (self.root / "scripts" / "memory-mcp").write_text("#!/bin/sh\n")
        self.project.mkdir()
        (self.project / "AGENTS.md").write_text("project-owned instructions\n")

    def install(self, *, memory=False):
        plan = lifecycle.install_plan(self.root, self.project, with_memory=memory)
        self.assertFalse(plan.conflicts, plan.conflicts)
        plan.apply()
        return plan

    def test_install_uses_generated_toml_only_and_is_idempotent(self):
        self.install()
        installed = self.project / ".codex" / "agents" / "builder.toml"
        self.assertEqual(installed.read_text(), 'name = "builder"\n')
        self.assertEqual((self.project / "AGENTS.md").read_text(), "project-owned instructions\n")
        manifest = json.loads((self.project / ".codex" / lifecycle.MANIFEST).read_text())
        self.assertEqual(set(manifest["agents"]), {"agents/builder.toml"})
        self.assertNotIn(str(self.project), json.dumps(manifest))
        again = lifecycle.install_plan(self.root, self.project, with_memory=False)
        self.assertEqual([change.action for change in again.changes], ["SKIP", "SKIP"])

    def test_dry_plan_and_doctor_are_read_only(self):
        before = snapshot(self.project)
        plan = lifecycle.install_plan(self.root, self.project, with_memory=False)
        self.assertTrue(plan.changes)
        self.assertEqual(snapshot(self.project), before)
        with patch.object(lifecycle, "_generated_state", return_value=("OK", "")), patch.object(lifecycle.shutil, "which", return_value="/node"):
            self.assertEqual(lifecycle.doctor(self.root, self.project, verbose=False), 1)
        self.assertEqual(snapshot(self.project), before)

    def test_unowned_agent_conflict_never_overwrites(self):
        target = self.project / ".codex" / "agents"
        target.mkdir(parents=True)
        agent = target / "builder.toml"
        agent.write_text("user-owned\n")
        plan = lifecycle.install_plan(self.root, self.project, with_memory=False)
        self.assertTrue(plan.conflicts)
        self.assertEqual(agent.read_text(), "user-owned\n")
        self.assertFalse((self.project / ".codex" / lifecycle.MANIFEST).exists())

    def test_owned_agent_updates_but_uninstall_preserves_later_edit(self):
        self.install()
        generated = self.root / ".generated" / "codex" / "agents" / "builder.toml"
        generated.write_text('name = "builder-v2"\n')
        update = lifecycle.install_plan(self.root, self.project, with_memory=False)
        self.assertIn("UPDATE", [change.action for change in update.changes])
        update.apply()
        installed = self.project / ".codex" / "agents" / "builder.toml"
        self.assertEqual(installed.read_text(), 'name = "builder-v2"\n')
        installed.write_text("user edit\n")
        removal = lifecycle.uninstall_plan(self.project)
        self.assertTrue(removal.conflicts)
        self.assertEqual(installed.read_text(), "user edit\n")

    def test_reinstall_preserves_manually_modified_managed_agent(self):
        self.install()
        installed = self.project / ".codex" / "agents" / "builder.toml"
        installed.write_text("user edit\n")
        generated = self.root / ".generated" / "codex" / "agents" / "builder.toml"
        generated.write_text('name = "builder-v2"\n')
        plan = lifecycle.install_plan(self.root, self.project, with_memory=False)
        self.assertTrue(plan.conflicts)
        self.assertTrue(any("managed agent was modified" in conflict for conflict in plan.conflicts))
        self.assertEqual(installed.read_text(), "user edit\n")
        with self.assertRaises(lifecycle.LifecycleError):
            plan.apply()
        self.assertEqual(installed.read_text(), "user edit\n")

    def test_memory_registration_is_explicit_and_preserves_other_tables(self):
        codex = self.project / ".codex"
        codex.mkdir()
        config = codex / "config.toml"
        config.write_text('[mcp_servers.other]\ncommand = "other"\n')
        self.install(memory=True)
        content = config.read_text()
        self.assertIn('[mcp_servers.other]', content)
        self.assertIn(lifecycle.MCP_HEADER, content)
        self.assertNotIn("github_pat_", content)
        manifest = (codex / lifecycle.MANIFEST).read_text()
        self.assertNotIn(str(self.project), manifest)
        self.assertNotIn(str(self.root), manifest)
        removal = lifecycle.uninstall_plan(self.project)
        self.assertFalse(removal.conflicts, removal.conflicts)
        removal.apply()
        self.assertEqual(config.read_text(), '[mcp_servers.other]\ncommand = "other"\n')

    def test_unowned_memory_table_is_never_replaced(self):
        codex = self.project / ".codex"
        codex.mkdir()
        config = codex / "config.toml"
        config.write_text(f'{lifecycle.MCP_HEADER}\ncommand = "user-command"\n')
        plan = lifecycle.install_plan(self.root, self.project, with_memory=True)
        self.assertTrue(plan.conflicts)
        self.assertEqual(config.read_text(), f'{lifecycle.MCP_HEADER}\ncommand = "user-command"\n')

    def test_modified_managed_memory_table_is_preserved_on_reinstall(self):
        self.install(memory=True)
        config = self.project / ".codex" / "config.toml"
        config.write_text(config.read_text().replace("memory-mcp", "user-edited-mcp"))
        plan = lifecycle.install_plan(self.root, self.project, with_memory=True)
        self.assertTrue(plan.conflicts)
        self.assertIn("user-edited-mcp", config.read_text())

    def test_symlinked_codex_directory_is_refused(self):
        outside = Path(self.directory.name) / "outside"
        outside.mkdir()
        (self.project / ".codex").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(lifecycle.LifecycleError, "symlinked .codex"):
            lifecycle.install_plan(self.root, self.project, with_memory=False)

    def test_symlinked_agent_file_and_manifest_path_escape_are_refused(self):
        agents = self.project / ".codex" / "agents"
        agents.mkdir(parents=True)
        outside = Path(self.directory.name) / "outside.toml"
        outside.write_text("outside\n")
        (agents / "builder.toml").symlink_to(outside)
        plan = lifecycle.install_plan(self.root, self.project, with_memory=False)
        self.assertTrue(plan.conflicts)
        self.assertEqual(outside.read_text(), "outside\n")
        (agents / "builder.toml").unlink()
        (self.project / ".codex" / lifecycle.MANIFEST).write_text(
            json.dumps({"version": 1, "agents": {"../outside.toml": "not-a-hash"}})
        )
        with self.assertRaisesRegex(lifecycle.LifecycleError, "Invalid managed agents"):
            lifecycle.uninstall_plan(self.project)

    def test_default_cli_refuses_toolkit_as_an_implicit_target(self):
        with patch.object(sys, "argv", ["codex", "install"]), patch.object(lifecycle.Path, "cwd", return_value=self.root):
            self.assertEqual(lifecycle.main(self.root), 2)

    def test_doctor_reports_generated_drift_without_repair(self):
        self.install()
        before = snapshot(self.project)
        with patch.object(lifecycle, "_generated_state", return_value=("DRIFT", "Run: oc sync codex")), patch.object(lifecycle.shutil, "which", return_value="/node"):
            self.assertEqual(lifecycle.doctor(self.root, self.project, verbose=True), 1)
        self.assertEqual(snapshot(self.project), before)


if __name__ == "__main__":
    unittest.main()
