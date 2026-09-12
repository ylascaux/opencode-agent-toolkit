import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.common import normalization


ROOT = Path(__file__).resolve().parents[1]


class SkillNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.skills = self.root / "skills"
        shutil.copytree(ROOT / "skills", self.skills)

    def load(self):
        with patch.object(normalization, "ROOT", self.root), patch.object(normalization, "SKILLS_DIR", self.skills):
            return normalization.load_normalized_skills()

    def test_discovers_a_deterministic_normalized_catalog(self):
        specs = self.load()
        self.assertEqual(list(specs), sorted(specs))
        self.assertEqual(specs["terraform-review"].tags, ("iac", "review", "terraform"))
        self.assertTrue(specs["security-review"].prompt)

    def test_rejects_malformed_names_and_metadata(self):
        for name, metadata in (
            ("Bad", {"name": "Bad", "description": "valid", "tags": []}),
            ("valid", {"name": "different", "description": "valid", "tags": []}),
            ("valid", {"name": "valid", "description": "bad\nvalue", "tags": []}),
            ("valid", {"name": "valid", "description": "valid", "tags": ["dup", "dup"]}),
            ("a" * 65, {"name": "a" * 65, "description": "valid", "tags": []}),
        ):
            with self.subTest(name=name, metadata=metadata):
                target = self.skills / name
                target.mkdir(exist_ok=True)
                (target / "skill.json").write_text(json.dumps(metadata))
                (target / "SKILL.md").write_text("body\n")
                with self.assertRaises(SystemExit):
                    self.load()
                shutil.rmtree(target)

    def test_rejects_duplicate_metadata_name(self):
        target = self.skills / "zz"
        target.mkdir()
        (target / "skill.json").write_text(json.dumps({
            "name": "terraform-review", "description": "valid", "tags": []
        }))
        (target / "SKILL.md").write_text("body\n")
        with self.assertRaisesRegex(SystemExit, "duplicate skill name"):
            self.load()

    def test_rejects_symlinked_skill_paths(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "SKILL.md").write_text("body\n")
        target = self.skills / "security-review"
        (target / "SKILL.md").unlink()
        (target / "SKILL.md").symlink_to(outside / "SKILL.md")
        with self.assertRaisesRegex(SystemExit, "symlinked"):
            self.load()


if __name__ == "__main__":
    unittest.main()
