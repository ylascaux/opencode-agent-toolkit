import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from memory_context import MemorySettings, normalize_remote, prepare_memory_context


def settings(directory: Path, *, enabled: bool = True, max_chars: int = 12000) -> MemorySettings:
    return MemorySettings(
        enabled=enabled,
        repo="",
        directory=directory,
        auto_sync=False,
        sync_interval_seconds=300,
        strict=True,
        max_chars=max_chars,
        project_override="",
        extra_hats=(),
    )


class MemoryContextTests(unittest.TestCase):
    def test_normalize_remote_supports_ssh_and_https(self):
        self.assertEqual(
            normalize_remote("git@github.com:ylascaux/opencode-agent-toolkit.git"),
            "ylascaux/opencode-agent-toolkit",
        )
        self.assertEqual(
            normalize_remote("https://github.com/ylascaux/opencode-agent-toolkit.git"),
            "ylascaux/opencode-agent-toolkit",
        )

    def test_disabled_memory_clears_stale_generated_context(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "toolkit"
            stale = root / ".generated" / "memory"
            stale.mkdir(parents=True)
            (stale / "common.md").write_text("stale")
            summary = prepare_memory_context(
                root,
                workdir=Path(tmp),
                settings=settings(Path(tmp) / "vault", enabled=False),
            )
            self.assertFalse(summary["enabled"])
            self.assertFalse(stale.exists())

    def test_project_workstyle_and_hats_are_rendered_but_inbox_is_not(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "toolkit"
            workdir = base / "sample-project"
            vault = base / "vault"
            workdir.mkdir()
            (vault / "projects" / "sample-project").mkdir(parents=True)
            (vault / "workstyle").mkdir()
            (vault / "hats").mkdir()
            (vault / "inbox").mkdir()
            (vault / "projects" / "index.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "projects": [
                            {
                                "id": "sample-project",
                                "match": {"names": ["sample-project"], "remotes": []},
                            }
                        ],
                    }
                )
            )
            (vault / "projects" / "sample-project" / "context.md").write_text(
                "---\ntype: project-context\n---\n\n# Project\nUse deterministic generation."
            )
            (vault / "workstyle" / "engineering.md").write_text(
                "# Engineering\nPrefer independent review."
            )
            (vault / "hats" / "assignments.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "default": [],
                        "agents": {"builder": ["software-engineer"]},
                    }
                )
            )
            (vault / "hats" / "software-engineer.md").write_text(
                "# Software engineer\nAdd regression tests."
            )
            (vault / "inbox" / "candidate.md").write_text("THIS MUST NOT BE INJECTED")

            summary = prepare_memory_context(root, workdir=workdir, settings=settings(vault))
            common = (root / ".generated" / "memory" / "common.md").read_text()
            builder = (root / ".generated" / "memory" / "agents" / "builder.md").read_text()
            self.assertEqual(summary["project_id"], "sample-project")
            self.assertIn("Use deterministic generation.", common)
            self.assertIn("Prefer independent review.", common)
            self.assertNotIn("THIS MUST NOT BE INJECTED", common)
            self.assertNotIn("type: project-context", common)
            self.assertIn("Add regression tests.", builder)

    def test_memory_context_is_bounded(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "toolkit"
            workdir = base / "project"
            vault = base / "vault"
            workdir.mkdir()
            (vault / "workstyle").mkdir(parents=True)
            (vault / "workstyle" / "large.md").write_text("# Large\n" + ("x" * 10000))
            prepare_memory_context(
                root,
                workdir=workdir,
                settings=settings(vault, max_chars=2400),
            )
            common = (root / ".generated" / "memory" / "common.md").read_text()
            self.assertLessEqual(len(common), 1900)
            self.assertIn("[Memory context truncated]", common)


if __name__ == "__main__":
    unittest.main()
