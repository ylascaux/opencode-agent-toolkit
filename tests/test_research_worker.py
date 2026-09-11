from __future__ import annotations

import unittest

from tools.research_worker.client import validate_api_base_url
from tools.research_worker.contracts import ContractError, ResearchOutput, build_toolkit_job, parse_external_job
from tools.research_worker.executor import ResearchExecutionError, parse_marked_result
from tools.research_worker.settings import WorkerSettings
from tools.research_worker.worker import ResearchWorker


def settings() -> WorkerSettings:
    return WorkerSettings(
        api_url="https://research.example.test",
        api_token="secret-test-token",
        worker_id="test-worker",
        worker_version="1",
        supported_job_types=("SUPPORT_LIFECYCLE",),
        max_parallel=1,
        poll_min_seconds=1,
        poll_max_seconds=2,
        request_timeout_seconds=5,
        execution_timeout_seconds=30,
        max_attempts=2,
        max_tier="medium",
        opencode_command="opencode2 --server http://127.0.0.1:4096",
        claim_path="/api/internal/research/v2/jobs/claim",
        result_path_template="/api/internal/research/v2/jobs/{job_id}/result",
    )


def job_payload() -> dict:
    return {
        "job_id": "job-1",
        "job_type": "SUPPORT_LIFECYCLE",
        "subject": {"type": "product", "id": "product-1", "slug": "example-device"},
        "requested_fields": ["security_support_end"],
        "requirements": {"preferred_source_types": ["MANUFACTURER"]},
        "schema_version": "1",
        "result_schema": {"type": "object"},
        "lease": {"generation": 3, "expires_at": "2026-09-11T12:00:00Z"},
    }


class ContractTests(unittest.TestCase):
    def test_neutral_job_parses(self):
        job = parse_external_job(job_payload())
        self.assertEqual(job.job_id, "job-1")
        self.assertEqual(job.requested_fields, ("security_support_end",))
        self.assertEqual(job.lease_generation, 3)

    def test_nested_remote_model_is_rejected(self):
        payload = job_payload()
        payload["requirements"] = {"routing": {"model": "remote-model"}}
        with self.assertRaises(ContractError):
            parse_external_job(payload)

    def test_nested_remote_command_is_rejected(self):
        payload = job_payload()
        payload["subject"]["metadata"] = {"command": "rm -rf /"}
        with self.assertRaises(ContractError):
            parse_external_job(payload)

    def test_local_policy_controls_toolkit_envelope(self):
        job = parse_external_job(job_payload())
        envelope = build_toolkit_job(job, max_tier="medium", max_attempts=2, max_parallel=1)
        self.assertEqual(envelope["policy"]["max_tier"], "medium")
        self.assertEqual(envelope["policy"]["max_attempts"], 2)
        serialized = repr(envelope)
        self.assertNotIn("remote-model", serialized)
        self.assertNotIn("provider", envelope)
        self.assertNotIn("agent", envelope)


class UrlTests(unittest.TestCase):
    def test_https_is_allowed(self):
        self.assertEqual(validate_api_base_url("https://research.example.com"), "https://research.example.com")

    def test_loopback_http_is_allowed_for_development(self):
        self.assertEqual(validate_api_base_url("http://127.0.0.1:8787"), "http://127.0.0.1:8787")

    def test_public_http_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_api_base_url("http://research.example.com")


class ExecutorTests(unittest.TestCase):
    def test_marked_result_parses(self):
        output = 'some progress\nOAT_RESEARCH_RESULT: {"status":"SUCCESS","data":{"security_support_end":"2030-10-01"},"evidence":[{"url":"https://example.com/support"}],"confidence":"HIGH","warnings":[]}\n'
        result = parse_marked_result(output)
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(result.data["security_support_end"], "2030-10-01")

    def test_missing_marker_is_rejected(self):
        with self.assertRaises(ResearchExecutionError):
            parse_marked_result('{"status":"SUCCESS"}')


class FakeClient:
    def __init__(self):
        self.jobs = [parse_external_job(job_payload())]
        self.submitted = []

    def claim(self):
        jobs, self.jobs = self.jobs, []
        return jobs

    def submit(self, job, result_id, result):
        self.submitted.append((job, result_id, result))


class FakeExecutor:
    def execute(self, job):
        return ResearchOutput(
            status="SUCCESS",
            data={"security_support_end": "2030-10-01"},
            evidence=[{"url": "https://example.com/support"}],
            confidence="HIGH",
            warnings=[],
        )


class WorkerTests(unittest.TestCase):
    def test_claim_execute_submit_cycle(self):
        client = FakeClient()
        worker = ResearchWorker(settings(), client, FakeExecutor())
        self.assertEqual(worker.run_once(), 1)
        self.assertEqual(len(client.submitted), 1)
        job, result_id, result = client.submitted[0]
        self.assertEqual(job.job_id, "job-1")
        self.assertTrue(result_id)
        self.assertEqual(result.status, "SUCCESS")


if __name__ == "__main__":
    unittest.main()
