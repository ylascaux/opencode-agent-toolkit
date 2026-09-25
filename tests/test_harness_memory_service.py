import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.common.harness_memory_service import HarnessMemoryService
from runtime.common.memory_v2 import MemoryV2Config, ProjectIdentity


class HarnessMemoryServiceTests(unittest.TestCase):
    def service(self):
        config = MemoryV2Config.from_env(
            {
                "OAT_MEMORY_BACKEND": "local",
                "OAT_MEMORY_LOCAL_PATH": "/tmp/oat-test-memory.sqlite",
                "OAT_MEMORY_NAMESPACE_PREFIX": "oat",
            }
        )
        identity = ProjectIdentity(
            root=Path("/tmp/project"),
            name="project",
            remote="git@github.com:owner/repo.git",
            project_id="owner/repo",
            source="git-remote",
        )
        return HarnessMemoryService(config, identity)

    def test_namespaces_are_owned_by_toolkit_not_backend_layout(self):
        service = self.service()
        self.assertEqual(service.project_namespace, "oat:project:owner/repo")
        self.assertEqual(service.global_namespace, "oat:user:default")

    def test_project_decision_maps_to_project_atom(self):
        service = self.service()
        calls = []

        def rpc(namespace, method, params=None):
            calls.append((namespace, method, params or {}))
            if method == "list_atoms":
                return {"items": [], "total": 0}
            if method == "create_atom":
                return {"status": "created", "atom": {"id": "a1", **(params or {})}}
            raise AssertionError(method)

        with patch.object(service, "_rpc", side_effect=rpc):
            result = service.remember(
                {
                    "kind": "decision",
                    "title": "Database",
                    "statement": "Use PostgreSQL for shared memory.",
                    "confidence": "high",
                }
            )

        self.assertEqual(result["status"], "created")
        create = [call for call in calls if call[1] == "create_atom"][0]
        self.assertEqual(create[0], "oat:project:owner/repo")
        self.assertEqual(create[2]["kind"], "Decision")
        self.assertEqual(create[2]["entity_type"], "Project")
        self.assertNotIn("dsn", str(create[2]).lower())

    def test_workstyle_maps_to_global_namespace(self):
        service = self.service()

        def rpc(namespace, method, params=None):
            if method == "list_atoms":
                return {"items": [], "total": 0}
            if method == "create_atom":
                self.assertEqual(namespace, "oat:user:default")
                self.assertEqual(params["kind"], "Preference")
                self.assertEqual(params["entity_type"], "User")
                return {"status": "created"}
            raise AssertionError(method)

        with patch.object(service, "_rpc", side_effect=rpc):
            result = service.remember(
                {
                    "kind": "workstyle",
                    "title": "Reviews",
                    "statement": "Prefer independent reviews for risky changes.",
                    "confidence": "high",
                }
            )
        self.assertEqual(result["status"], "created")

    def test_exact_duplicate_is_not_rewritten(self):
        service = self.service()
        assertion = "Keep the agent catalog small."

        def rpc(_namespace, method, params=None):
            if method == "list_atoms":
                return {"items": [{"id": "existing", "assertion": assertion, "kind": "Fact"}], "total": 1}
            raise AssertionError("create_atom must not be called for an exact duplicate")

        with patch.object(service, "_rpc", side_effect=rpc):
            result = service.remember(
                {
                    "kind": "project_fact",
                    "title": "Catalog",
                    "statement": assertion,
                    "confidence": "high",
                }
            )
        self.assertEqual(result["status"], "duplicate")

    def test_render_combines_project_and_global_context_with_bound(self):
        service = self.service()

        def rpc(namespace, method, params=None):
            self.assertEqual(method, "list_atoms")
            assertion = "Project fact" if namespace == service.project_namespace else "User preference"
            return {"items": [{"id": "x", "assertion": assertion, "kind": "Fact"}], "total": 1}

        with patch.object(service, "_rpc", side_effect=rpc):
            result = service.render(max_chars=2000)
        self.assertIn("Project fact", result["text"])
        self.assertIn("User preference", result["text"])
        self.assertLessEqual(len(result["text"]), 2000)


if __name__ == "__main__":
    unittest.main()
