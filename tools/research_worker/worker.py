from __future__ import annotations

import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Protocol

from .client import ResearchApiClient, ResearchApiError
from .models import ExternalResearchJob, ResultSubmission, ToolkitResearchResult
from .protocol import build_toolkit_job
from .settings import WorkerSettings

logger = logging.getLogger("oat.research_worker")


class Executor(Protocol):
    def execute(self, toolkit_job: dict) -> ToolkitResearchResult: ...


@dataclass
class ResearchWorker:
    settings: WorkerSettings
    client: ResearchApiClient
    executor: Executor

    def _process(self, job: ExternalResearchJob) -> str:
        toolkit_job = build_toolkit_job(job, self.settings)
        started = time.monotonic()
        result = self.executor.execute(toolkit_job)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "research completed job_id=%s job_type=%s status=%s confidence=%s duration_ms=%s",
            job.id,
            job.job_type,
            result.status,
            result.confidence,
            elapsed_ms,
        )
        submission = ResultSubmission(
            result_id=str(uuid.uuid4()),
            worker_id=self.settings.worker_id,
            worker_version=self.settings.worker_version,
            lease_generation=job.lease.generation,
            result=result,
        )
        self.client.submit(job, submission)
        return job.id

    def run_once(self) -> int:
        jobs = self.client.claim()
        if not jobs:
            return 0
        completed = 0
        with ThreadPoolExecutor(max_workers=self.settings.max_parallel) as pool:
            futures = {pool.submit(self._process, job): job for job in jobs}
            for future in as_completed(futures):
                job = futures[future]
                try:
                    future.result()
                    completed += 1
                except Exception as error:
                    # Do not fabricate a Research Result on local execution failure.
                    # The external lease expires and the caller-owned queue decides retry/dead-letter policy.
                    logger.error("research failed job_id=%s job_type=%s error=%s", job.id, job.job_type, error)
        return completed

    def run_forever(self) -> None:
        delay = self.settings.poll_min_seconds
        while True:
            try:
                completed = self.run_once()
                if completed:
                    delay = self.settings.poll_min_seconds
                    continue
                time.sleep(delay)
                delay = min(self.settings.poll_max_seconds, max(self.settings.poll_min_seconds, delay * 2))
            except ResearchApiError as error:
                logger.warning("research API unavailable: %s", error)
                time.sleep(delay)
                delay = min(self.settings.poll_max_seconds, max(self.settings.poll_min_seconds, delay * 2))
