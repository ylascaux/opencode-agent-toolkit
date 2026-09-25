from __future__ import annotations

import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from runtime.common.harness_memory_service import HarnessMemoryService
from runtime.common.memory_v2 import MemoryV2Config, ProjectIdentity

DSN = os.getenv("OAT_TEST_POSTGRES_DSN", "").strip()


@unittest.skipUnless(DSN, "OAT_TEST_POSTGRES_DSN is required")
class HarnessMemoryPostgresTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = MemoryV2Config.from_env(
            {
                "OAT_MEMORY_BACKEND": "postgres",
                "OAT_MEMORY_POSTGRES_DSN": DSN,
                "OAT_MEMORY_NAMESPACE_PREFIX": "oat-ci",
            }
        )
        self.identity = ProjectIdentity(
            root=Path("/tmp/ci-project"),
            name="ci-project",
            remote="git@github.com:owner/ci-project.git",
            project_id="owner/ci-project",
            source="git-remote",
        )

    def service(self) -> HarnessMemoryService:
        return HarnessMemoryService(self.config, self.identity)

    def test_two_clients_share_project_and_global_memory(self) -> None:
        first = self.service()
        second = self.service()

        first.remember(
            {
                "kind": "decision",
                "title": "Client A",
                "statement": "Client A stores a decision visible to client B.",
                "confidence": "high",
            }
        )
        from_second = second.render()["text"]
        self.assertIn("Client A stores a decision visible to client B.", from_second)

        second.remember(
            {
                "kind": "workstyle",
                "title": "Client B",
                "statement": "Client B stores a shared workstyle visible to client A.",
                "confidence": "high",
            }
        )
        from_first = first.render()["text"]
        self.assertIn("Client B stores a shared workstyle visible to client A.", from_first)

    def test_identical_concurrent_writers_deduplicate(self) -> None:
        self.service().status()
        assertion = "Concurrent identical writers should converge to one durable atom."

        def write(_index: int) -> None:
            self.service().remember(
                {
                    "kind": "project_fact",
                    "title": "Concurrent identical",
                    "statement": assertion,
                    "confidence": "high",
                }
            )

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(write, range(4)))

        items = self.service()._list(self.service().project_namespace, query=assertion, limit=20)
        exact = [item for item in items if str(item.get("assertion") or "").strip() == assertion]
        self.assertEqual(len(exact), 1, exact)

    def test_distinct_concurrent_writers_do_not_lose_data(self) -> None:
        # Warm the schema before the concurrent phase so this test targets writer
        # concurrency rather than first-boot DDL races.
        self.service().status()

        def write(index: int) -> None:
            self.service().remember(
                {
                    "kind": "project_fact",
                    "title": f"Concurrent {index}",
                    "statement": f"Concurrent writer fact {index}.",
                    "confidence": "high",
                }
            )

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(write, range(1, 5)))

        text = self.service().render(max_chars=20_000)["text"]
        for index in range(1, 5):
            self.assertIn(f"Concurrent writer fact {index}.", text)


if __name__ == "__main__":
    unittest.main()
