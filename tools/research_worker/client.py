from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from .contracts import ExternalResearchJob, ResearchOutput, parse_external_job
from .settings import WorkerSettings

MAX_RESPONSE_BYTES = 256 * 1024


class ResearchApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes


def validate_api_base_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.username or parsed.password:
        raise ValueError("Research API URL must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("Research API URL must not contain a query or fragment")
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError("Research API URL must include a host")
    is_loopback = hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not (parsed.scheme == "http" and is_loopback):
        raise ValueError("Research API URL must use HTTPS; HTTP is allowed only for loopback development")
    return value.rstrip("/")


class ResearchApiClient:
    def __init__(self, settings: WorkerSettings, opener: Any | None = None):
        self.settings = settings
        self.base_url = validate_api_base_url(settings.api_url)
        self.opener = opener or urllib.request.build_opener()

    def _request(self, method: str, path: str, payload: dict[str, Any]) -> HttpResponse:
        url = urllib.parse.urljoin(f"{self.base_url}/", path.lstrip("/"))
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.settings.api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": f"opencode-agent-toolkit-research-worker/{self.settings.worker_version}",
            },
        )
        try:
            with self.opener.open(request, timeout=self.settings.request_timeout_seconds) as response:
                data = response.read(MAX_RESPONSE_BYTES + 1)
                if len(data) > MAX_RESPONSE_BYTES:
                    raise ResearchApiError("Research API response exceeds 256 KiB")
                return HttpResponse(status=response.status, body=data)
        except urllib.error.HTTPError as error:
            data = error.read(MAX_RESPONSE_BYTES + 1)
            if len(data) > MAX_RESPONSE_BYTES:
                data = b""
            raise ResearchApiError(f"Research API returned HTTP {error.code}") from None
        except urllib.error.URLError as error:
            raise ResearchApiError(f"Research API request failed: {error.reason}") from None

    @staticmethod
    def _json(response: HttpResponse) -> Any:
        if not response.body:
            return None
        try:
            return json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ResearchApiError("Research API returned invalid JSON") from error

    def claim(self) -> list[ExternalResearchJob]:
        response = self._request(
            "POST",
            self.settings.claim_path,
            {
                "worker_id": self.settings.worker_id,
                "worker_version": self.settings.worker_version,
                "supported_job_types": list(self.settings.supported_job_types),
                "max_jobs": self.settings.max_parallel,
            },
        )
        if response.status == 204:
            return []
        if response.status != 200:
            raise ResearchApiError(f"Unexpected claim response status: {response.status}")
        payload = self._json(response)
        if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
            raise ResearchApiError("Claim response must contain a jobs array")
        if len(payload["jobs"]) > self.settings.max_parallel:
            raise ResearchApiError("Claim response exceeds the worker's local parallelism limit")
        try:
            return [parse_external_job(item) for item in payload["jobs"]]
        except Exception as error:
            raise ResearchApiError(f"Claim response failed validation: {error}") from error

    def submit(self, job: ExternalResearchJob, result_id: str, result: ResearchOutput) -> None:
        if job.lease_generation is None:
            raise ResearchApiError("Claimed job is missing lease.generation")
        path = self.settings.result_path_template.format(job_id=urllib.parse.quote(job.job_id, safe=""))
        response = self._request(
            "POST",
            path,
            {
                "job_id": job.job_id,
                "result_id": result_id,
                "worker_id": self.settings.worker_id,
                "worker_version": self.settings.worker_version,
                "lease_generation": job.lease_generation,
                "schema_version": job.schema_version,
                **result.as_dict(),
            },
        )
        if response.status not in {200, 201, 202, 204}:
            raise ResearchApiError(f"Unexpected result response status: {response.status}")
