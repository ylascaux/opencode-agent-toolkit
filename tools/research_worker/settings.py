from __future__ import annotations

import os
import socket
from dataclasses import dataclass


def _int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    value = default if raw in (None, "") else int(raw)
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _csv_env(name: str) -> tuple[str, ...]:
    values = tuple(value.strip() for value in os.getenv(name, "").split(",") if value.strip())
    if not values:
        raise ValueError(f"{name} must contain at least one job type")
    if len(set(values)) != len(values):
        raise ValueError(f"{name} contains duplicate job types")
    return values


@dataclass(frozen=True)
class WorkerSettings:
    api_url: str
    api_token: str
    worker_id: str
    worker_version: str
    supported_job_types: tuple[str, ...]
    max_parallel: int
    poll_min_seconds: int
    poll_max_seconds: int
    request_timeout_seconds: int
    execution_timeout_seconds: int
    max_attempts: int
    max_tier: str
    opencode_command: str
    opencode_major: str
    claim_path: str
    result_path_template: str


def load_settings() -> WorkerSettings:
    api_url = os.getenv("OAT_RESEARCH_API_URL", "").strip()
    api_token = os.getenv("OAT_RESEARCH_API_TOKEN", "").strip()
    if not api_url:
        raise ValueError("OAT_RESEARCH_API_URL is required")
    if not api_token:
        raise ValueError("OAT_RESEARCH_API_TOKEN is required")

    max_tier = os.getenv("OAT_RESEARCH_MAX_TIER", "high").strip().lower()
    if max_tier not in {"low", "medium", "high"}:
        raise ValueError("OAT_RESEARCH_MAX_TIER must be low, medium, or high")

    opencode_major = os.getenv("OAT_RESEARCH_OPENCODE_MAJOR", "2").strip() or "2"
    if opencode_major not in {"1", "2", "auto"}:
        raise ValueError("OAT_RESEARCH_OPENCODE_MAJOR must be 1, 2, or auto")

    poll_min = _int_env("OAT_RESEARCH_POLL_MIN_SECONDS", 5, 1, 3600)
    poll_max = _int_env("OAT_RESEARCH_POLL_MAX_SECONDS", 30, poll_min, 3600)

    return WorkerSettings(
        api_url=api_url,
        api_token=api_token,
        worker_id=os.getenv("OAT_RESEARCH_WORKER_ID", socket.gethostname()).strip() or socket.gethostname(),
        worker_version=os.getenv("OAT_RESEARCH_WORKER_VERSION", "1").strip() or "1",
        supported_job_types=_csv_env("OAT_RESEARCH_JOB_TYPES"),
        max_parallel=_int_env("OAT_RESEARCH_MAX_PARALLEL", 1, 1, 8),
        poll_min_seconds=poll_min,
        poll_max_seconds=poll_max,
        request_timeout_seconds=_int_env("OAT_RESEARCH_REQUEST_TIMEOUT_SECONDS", 20, 1, 300),
        execution_timeout_seconds=_int_env("OAT_RESEARCH_EXECUTION_TIMEOUT_SECONDS", 900, 30, 7200),
        max_attempts=_int_env("OAT_RESEARCH_MAX_ATTEMPTS", 2, 1, 5),
        max_tier=max_tier,
        # The toolkit launcher is the safe default because it preserves the user's
        # configured native/Docker runtime and persistent OpenCode server behavior.
        # A custom command remains a trusted LOCAL setting; it is never accepted
        # from a claimed research job.
        opencode_command=os.getenv(
            "OAT_RESEARCH_OPENCODE_COMMAND",
            "bash scripts/opencode-agents",
        ).strip(),
        opencode_major=opencode_major,
        claim_path=os.getenv("OAT_RESEARCH_CLAIM_PATH", "/api/internal/research/v2/jobs/claim").strip(),
        result_path_template=os.getenv(
            "OAT_RESEARCH_RESULT_PATH_TEMPLATE",
            "/api/internal/research/v2/jobs/{job_id}/result",
        ).strip(),
    )
