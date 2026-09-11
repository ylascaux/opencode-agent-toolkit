from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from .contracts import ContractError, ExternalResearchJob, parse_external_job

MAX_RESPONSE_BYTES = 256 * 1024


class ResearchApiError(RuntimeError):
    pass


def validate_api_base_url(value: str) -> str:
    try:
        parsed = urllib.parse.urlsplit(value)
    except ValueError as exc:
        raise ResearchApiError("invalid research API URL") from exc
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ResearchApiError("research API URL must not include credentials, query parameters, or fragments")
    hostname = (parsed.hostname or "").lower()
    is_loopback = hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme == "https":
        pass
    elif parsed.scheme == "http" and is_loopback:
        pass
    else:
        raise ResearchApiError("research API URL must use HTTPS; HTTP is allowed only for loopback development")
    if not hostname:
        raise ResearchApiError("research API URL must include a hostname")
    path = parsed.path.rstrip("/")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _join(base: str, path: str) -> str:
    return base.rstrip("/") + "/" + path.lstrip("/")


@dataclass(frozen=True)
class ClaimBatch:
    jobs: tuple[ExternalResearchJob, ...]


class ResearchApiClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout_seconds: float = 15.0,
        claim_path: str = "/api/internal/research/v2/jobs/claim",
        result_path_template: str = "/api/internal/research/v2/jobs/{job_id}/result",
    ) -> None:
        self.base_url = validate_api_base_url(base_url)
        self.token = token.strip()
        if not self.token:
            raise ResearchApiError("research API token is required")
        self.timeout_seconds = timeout_seconds
        self.claim_path = claim_path
        self.result_path_template = result_path_template

    def _post(self, path: str, payload: dict[str, Any], *, allow_no_content: bool = False) -> Any:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            _join(self.base_url, path),
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "opencode-agent-toolkit-research-worker/1",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                if response.status == 204 and allow_no_content:
                    return None
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise ResearchApiError("research API response exceeds 256 KiB")
                if not raw:
                    return None
                try:
                    return json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ResearchApiError("research API returned invalid JSON") from exc
        except urllib.error.HTTPError as exc:
            raw = exc.read(4096)
            detail = raw.decode("utf-8", errors="replace").strip()
            detail = detail[:1000]
            raise ResearchApiError(f"research API returned HTTP {exc.code}: {detail or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise ResearchApiError(f"research API request failed: {exc.reason}") from exc

    def claim(
        self,
        *,
        worker_id: str,
        worker_version: str,
        supported_job_types: tuple[str, ...],
        max_jobs: int,
    ) -> ClaimBatch:
        payload = {
            "worker_id": worker_id,
            "worker_version": worker_version,
            "supported_job_types": list(supported_job_types),
            "max_jobs": max_jobs,
        }
        raw = self._post(self.claim_path, payload, allow_no_content=True)
        if raw is None:
            return ClaimBatch(jobs=())
        if not isinstance(raw, dict):
            raise ResearchApiError("claim response must be an object")
        jobs = raw.get("jobs", [])
        if not isinstance(jobs, list):
            raise ResearchApiError("claim response jobs must be an array")
        parsed: list[ExternalResearchJob] = []
        try:
            for item in jobs:
                parsed.append(parse_external_job(item))
        except ContractError as exc:
            raise ResearchApiError(f"claim response contains an invalid job: {exc}") from exc
        return ClaimBatch(jobs=tuple(parsed))

    def submit_result(self, job_id: str, payload: dict[str, Any]) -> Any:
        safe_job_id = urllib.parse.quote(job_id, safe="")
        path = self.result_path_template.format(job_id=safe_job_id)
        return self._post(path, payload)
