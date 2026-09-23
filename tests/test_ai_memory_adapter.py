import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "scripts" / "ai-memory-adapter"


def make_upstream(root: Path) -> Path:
    home = root / "create-ai-memory"
    (home / "shell").mkdir(parents=True)
    (home / "vault-template/_projects").mkdir(parents=True)
    (home / "vault-template/_session_logs").mkdir(parents=True)
    (home / "vault-template/_lessons").mkdir(parents=True)
    (home / "shell/ai-mem.zsh").write_text("# fixture\n")
    (home / "vault-template/_Global_Profile.md").write_text("# Profile\n")
    (home / "vault-template/_Standards.md").write_text("# Standards\n")
    (home / "vault-template/_projects/_project_template.md").write_text(
        "---\ntype: ai-project-context\nproject_name: [Insert Project Name]\n---\n# [Insert Project Name]\n"
    )
    (home / "vault-template/_session_logs/_session_template.md").write_text(
        "---\ntype: ai-session-log\nproject: \"[[{{project_name}}]]\"\n---\n# Session Outcome\n"
    )
    (home / "vault-template/_lessons/_lesson_template.md").write_text(
        "---\ntype: ai-lesson\ntopic: {{topic}}\n---\n# {{topic}}\n"
    )
    return home


class AiMemoryAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.upstream = make_upstream(self.base)
        self.vault = self.base / "vault"
        self.vault.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.vault, check=True)
        (self.vault / "projects").mkdir()
        (self.vault / "workstyle").mkdir()
        (self.vault / "workstyle/preferences.md").write_text("# Preferences\n")
        (self.vault / "workstyle/engineering.md").write_text("# Engineering\n")
        self.project = self.base / "demo"
        self.project.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.project, check=True)

    def run_setup(self):
        return subprocess.run(
            [
                "python3",
                str(ADAPTER),
                "setup",
                "--root",
                str(self.vault),
                "--home",
                str(self.upstream),
                "--cwd",
                str(self.project),
            ],
            text=True,
            capture_output=True,
        )

    def test_setup_maps_upstream_layout_onto_structured_vault(self):
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "demo")

        self.assertTrue((self.vault / "_Global_Profile.md").is_symlink())
        self.assertEqual((self.vault / "_Global_Profile.md").resolve(), self.vault / "workstyle/preferences.md")
        self.assertEqual((self.vault / "_Standards.md").resolve(), self.vault / "workstyle/engineering.md")
        self.assertEqual((self.vault / "_session_logs").resolve(), self.vault / "sessions")
        self.assertEqual((self.vault / "_lessons").resolve(), self.vault / "lessons")
        self.assertEqual((self.vault / "_projects/demo.md").resolve(), self.vault / "projects/demo/context.md")
        self.assertIn("demo", (self.vault / "projects/demo/context.md").read_text())
        self.assertTrue((self.vault / "sessions/_session_template.md").is_file())
        self.assertTrue((self.vault / "lessons/_lesson_template.md").is_file())

        exclude = (self.vault / ".git/info/exclude").read_text()
        for entry in ("_Global_Profile.md", "_Standards.md", "_projects/", "_session_logs", "_lessons"):
            self.assertIn(entry, exclude)

    def test_projects_index_can_map_remote_to_existing_memory_project(self):
        subprocess.run(
            ["git", "remote", "add", "origin", "git@github.com:ylascaux/real-repository.git"],
            cwd=self.project,
            check=True,
        )
        (self.vault / "projects/index.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "projects": [
                        {
                            "id": "mapped-project",
                            "match": {
                                "names": [],
                                "remotes": ["ylascaux/real-repository"],
                            },
                        }
                    ],
                }
            )
        )
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "mapped-project")
        self.assertTrue((self.vault / "projects/mapped-project/context.md").is_file())

    def test_setup_refuses_to_replace_user_owned_compatibility_path(self):
        (self.vault / "_Global_Profile.md").write_text("keep me\n")
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to replace existing path", result.stderr)
        self.assertEqual((self.vault / "_Global_Profile.md").read_text(), "keep me\n")


if __name__ == "__main__":
    unittest.main()
