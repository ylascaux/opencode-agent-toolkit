import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")


class ReleaseMetadataTests(unittest.TestCase):
    def test_version_is_semver_and_has_matching_changelog_section(self):
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(version, SEMVER)
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"## [{version}]", changelog)

    def test_release_check_metadata_only_passes_for_current_version(self):
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        result = subprocess.run(
            [sys.executable, "-B", "scripts/release-check", "--metadata-only", "--tag", f"v{version}"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"release metadata: OK (v{version})", result.stdout)

    def test_release_docs_require_merge_before_tag(self):
        for path in (ROOT / "docs/en/RELEASE.md", ROOT / "docs/fr/RELEASE.md"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("VERSION", text)
            self.assertIn("CHANGELOG.md", text)
            self.assertIn("scripts/release-check", text)
            self.assertIn("git tag -a", text)


if __name__ == "__main__":
    unittest.main()
