import importlib.util
import tempfile
import unittest
from pathlib import Path

from runtime.common.harness_memory_service import HarnessMemoryService
from runtime.common.memory_v2 import MemoryV2Config, ProjectIdentity

HAS_HARNESS_MEMORY = importlib.util.find_spec("harness_memory") is not None


@unittest.skipUnless(HAS_HARNESS_MEMORY, "harness-memory is installed in the managed/container V2 runtime")
class HarnessMemoryRuntimeSmokeTests(unittest.TestCase):
    def test_real_sqlite_bridge_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "memory.sqlite"
            config = MemoryV2Config.from_env(
                {
                    "OAT_MEMORY_BACKEND": "local",
                    "OAT_MEMORY_LOCAL_PATH": str(db),
                    "OAT_MEMORY_NAMESPACE_PREFIX": "oat-test",
                }
            )
            identity = ProjectIdentity(
                root=Path(tmp),
                name="repo",
                remote="git@github.com:owner/repo.git",
                project_id="owner/repo",
                source="git-remote",
            )
            service = HarnessMemoryService(config, identity)
            created = service.remember(
                {
                    "kind": "decision",
                    "title": "Runtime smoke",
                    "statement": "Use the real harness-memory bridge in CI.",
                    "confidence": "high",
                }
            )
            self.assertEqual(created["status"], "created")

            status = service.status()
            self.assertGreaterEqual(status["project_counts"].get("atoms", 0), 1)

            rendered = service.render()
            self.assertIn("Use the real harness-memory bridge in CI.", rendered["text"])

            duplicate = service.remember(
                {
                    "kind": "decision",
                    "title": "Runtime smoke",
                    "statement": "Use the real harness-memory bridge in CI.",
                    "confidence": "high",
                }
            )
            self.assertEqual(duplicate["status"], "duplicate")


if __name__ == "__main__":
    unittest.main()
