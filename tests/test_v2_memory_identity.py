import tempfile
import unittest
from pathlib import Path
from runtime.common.memory_v2 import MemoryV2Config, normalize_remote, resolve_project_identity


class V2MemoryIdentityTests(unittest.TestCase):
    def test_remote_normalization_is_path_independent(self):
        for remote in (
            "git@github.com:ylascaux/opencode-agent-toolkit.git",
            "ssh://git@github.com/ylascaux/opencode-agent-toolkit.git",
            "https://github.com/ylascaux/opencode-agent-toolkit.git",
        ):
            with self.subTest(remote=remote):
                self.assertEqual(normalize_remote(remote), "ylascaux/opencode-agent-toolkit")

    def test_project_override_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity = resolve_project_identity(tmp, environ={"OAT_MEMORY_PROJECT": "custom/project"})
        self.assertEqual(identity.project_id, "custom/project")
        self.assertEqual(identity.source, "override")

    def test_namespace_is_stable_and_backend_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity = resolve_project_identity(tmp, environ={"OAT_MEMORY_PROJECT": "owner/repo"})
        config = MemoryV2Config.from_env(
            {
                "OAT_MEMORY_BACKEND": "postgres",
                "OAT_MEMORY_POSTGRES_DSN": "postgresql://user:secret@db.example:5432/memory",
                "OAT_MEMORY_NAMESPACE_PREFIX": "oat",
            }
        )
        self.assertEqual(config.namespace_for(identity), "oat:project:owner/repo")
        self.assertTrue(config.shared)
        self.assertEqual(config.masked_dsn(), "postgresql://user:***@db.example:5432/memory")

    def test_postgres_requires_dsn(self):
        with self.assertRaises(ValueError):
            MemoryV2Config.from_env({"OAT_MEMORY_BACKEND": "postgres"})

    def test_legacy_is_the_safe_default_until_cutover(self):
        config = MemoryV2Config.from_env({})
        self.assertEqual(config.backend, "legacy")
        self.assertFalse(config.shared)


if __name__ == "__main__":
    unittest.main()
