from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

FORBIDDEN_CONTROL_KEYS = {
    "agent",
    "attach",
    "callback_url",
    "command",
    "local_path",
    "model",
    "opencode",
    "opencode_config",
    "prompt",
    "provider",
    "reasoning",
    "reasoning_effort",
    "repository_path",
    "server",
    "shell",
    "temperature",
    "thinking",
    "tool",
}

RESULT_STATUSES = {"SUCCESS", "PARTIAL", "NO_DATA", "CONFLICT", "FAILED"}
CONFIDENCE_VALUES = {"HIGH", "MEDIUM", "LOW"}
TIER_VALUES = {"low", "medium", "high"}


class ContractError(ValueError):
    pass


@dataclass(frozen=True)
class ExternalResearchJob:
    job_id: str
    job_type: str
    subject: dict[str, Any]
    requested_fields: tuple[str, ...]
    requirements: dict[str, Any]
    schema_version: str
    target_schema: dict[str, Any] | None
    metadata: dict[str, Any]
    lease_generation: int | None
    lease_expires_at: str | None


@dataclass(frozen=True)
class ResearchOutput:
    status: str
    data: Any
    evidence: list[dict[str, Any]]
    confidence: str
    warnings: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "data": self.data,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


def _nonempty_string(value: Any, field: str, *, maximum: int = 512) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field} must be a non-empty string")
    value = value.strip()
    if len(value) > maximum:
        raise ContractError(f"{field} exceeds {maximum} characters")
    return value


def _dict(value: Any, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ContractError(f"{field} must be an object")
    return value


def _normalized_key(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_")


def _reject_top_level_remote_controls(payload: dict[str, Any]) -> None:
    present = sorted(key for key in payload if _normalized_key(key) in FORBIDDEN_CONTROL_KEYS)
    if present:
        raise ContractError("remote execution controls are forbidden: " + ", ".join(present))


def parse_external_job(payload: Any) -> ExternalResearchJob:
    if not isinstance(payload, dict):
        raise ContractError("job must be an object")
    # Only the envelope can control worker execution. Nested subject/requirements/
    # schema/metadata values are opaque untrusted domain data and may legitimately
    # contain names such as "model" or "provider". They are never interpreted as
    # local execution controls and are passed to research-runner as DATA.
    _reject_top_level_remote_controls(payload)

    allowed = {
        "id",
        "job_id",
        "job_type",
        "subject",
        "requested_fields",
        "requirements",
        "schema_version",
        "target_schema",
        "result_schema",
        "metadata",
        "priority",
        "lease",
    }
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ContractError("unsupported job field(s): " + ", ".join(unknown))

    raw_job_id = payload.get("job_id", payload.get("id"))
    job_id = _nonempty_string(raw_job_id, "job_id", maximum=256)
    job_type = _nonempty_string(payload.get("job_type"), "job_type", maximum=128)
    schema_version = _nonempty_string(payload.get("schema_version", "1"), "schema_version", maximum=32)

    subject = _dict(payload.get("subject"), "subject")
    if not subject:
        raise ContractError("subject must not be empty")
    if len(json.dumps(subject, ensure_ascii=False)) > 16_384:
        raise ContractError("subject exceeds 16 KiB")

    raw_fields = payload.get("requested_fields")
    if not isinstance(raw_fields, list) or not raw_fields:
        raise ContractError("requested_fields must be a non-empty array")
    if len(raw_fields) > 64:
        raise ContractError("requested_fields exceeds 64 entries")
    fields: list[str] = []
    for index, field in enumerate(raw_fields):
        fields.append(_nonempty_string(field, f"requested_fields[{index}]", maximum=256))
    if len(set(fields)) != len(fields):
        raise ContractError("requested_fields must be unique")

    requirements = _dict(payload.get("requirements"), "requirements")
    metadata = _dict(payload.get("metadata"), "metadata")
    if len(json.dumps(requirements, ensure_ascii=False)) > 16_384:
        raise ContractError("requirements exceeds 16 KiB")
    if len(json.dumps(metadata, ensure_ascii=False)) > 16_384:
        raise ContractError("metadata exceeds 16 KiB")

    target_schema = payload.get("target_schema", payload.get("result_schema"))
    if payload.get("target_schema") is not None and payload.get("result_schema") is not None and payload["target_schema"] != payload["result_schema"]:
        raise ContractError("target_schema and result_schema disagree")
    if target_schema is not None and not isinstance(target_schema, dict):
        raise ContractError("target_schema/result_schema must be an object when supplied")
    if target_schema is not None and len(json.dumps(target_schema, ensure_ascii=False)) > 32_768:
        raise ContractError("target schema exceeds 32 KiB")

    lease = _dict(payload.get("lease"), "lease")
    lease_generation = lease.get("generation")
    if lease_generation is not None and (not isinstance(lease_generation, int) or isinstance(lease_generation, bool) or lease_generation < 1):
        raise ContractError("lease.generation must be a positive integer")
    lease_expires_at = lease.get("expires_at")
    if lease_expires_at is not None:
        lease_expires_at = _nonempty_string(lease_expires_at, "lease.expires_at", maximum=128)

    return ExternalResearchJob(
        job_id=job_id,
        job_type=job_type,
        subject=subject,
        requested_fields=tuple(fields),
        requirements=requirements,
        schema_version=schema_version,
        target_schema=target_schema,
        metadata=metadata,
        lease_generation=lease_generation,
        lease_expires_at=lease_expires_at,
    )


def build_toolkit_job(
    job: ExternalResearchJob,
    *,
    max_tier: str = "high",
    max_attempts: int = 2,
    max_parallel: int = 3,
) -> dict[str, Any]:
    if max_tier not in TIER_VALUES:
        raise ContractError(f"invalid local max_tier: {max_tier}")
    if max_attempts < 1 or max_attempts > 5:
        raise ContractError("local max_attempts must be between 1 and 5")
    if max_parallel < 1 or max_parallel > 32:
        raise ContractError("local max_parallel must be between 1 and 32")

    evidence_requirements = [
        "Preserve source provenance for every asserted requested field.",
        "Do not invent unknown values; return NO_DATA or PARTIAL when evidence is insufficient.",
    ]
    preferred = job.requirements.get("preferred_source_types")
    if isinstance(preferred, list) and preferred:
        safe_types = [str(value)[:80] for value in preferred[:20]]
        evidence_requirements.append("Prefer source types requested by the caller when authoritative: " + ", ".join(safe_types))

    result: dict[str, Any] = {
        "schema_version": "1",
        "job_id": job.job_id,
        "stage": "pipeline",
        "task": f"{job.job_type}: research requested fields {', '.join(job.requested_fields)}",
        "input": {
            "subject": job.subject,
            "requested_fields": list(job.requested_fields),
            "requirements": job.requirements,
            "metadata": job.metadata,
        },
        "evidence_requirements": evidence_requirements,
        "policy": {
            "max_attempts": max_attempts,
            "max_parallel": max_parallel,
            "max_tier": max_tier,
            "require_evidence": True,
            "allow_same_tier_retry": True,
        },
    }
    if job.target_schema is not None:
        result["target_schema"] = job.target_schema
    return result


def validate_research_output(payload: Any) -> ResearchOutput:
    if not isinstance(payload, dict):
        raise ContractError("research output must be an object")

    allowed = {"status", "data", "evidence", "confidence", "warnings"}
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ContractError("unsupported research output field(s): " + ", ".join(unknown))

    status = _nonempty_string(payload.get("status"), "status", maximum=32).upper()
    if status not in RESULT_STATUSES:
        raise ContractError(f"unsupported status: {status}")
    confidence = _nonempty_string(payload.get("confidence"), "confidence", maximum=16).upper()
    if confidence not in CONFIDENCE_VALUES:
        raise ContractError(f"unsupported confidence: {confidence}")

    evidence = payload.get("evidence", [])
    if not isinstance(evidence, list):
        raise ContractError("evidence must be an array")
    if len(evidence) > 50:
        raise ContractError("evidence exceeds 50 entries")
    normalized_evidence: list[dict[str, Any]] = []
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            raise ContractError(f"evidence[{index}] must be an object")
        if len(json.dumps(item, ensure_ascii=False)) > 8_192:
            raise ContractError(f"evidence[{index}] exceeds 8 KiB")
        normalized_evidence.append(item)

    warnings = payload.get("warnings", [])
    if not isinstance(warnings, list) or len(warnings) > 30:
        raise ContractError("warnings must be an array of at most 30 strings")
    normalized_warnings = [_nonempty_string(value, f"warnings[{index}]", maximum=500) for index, value in enumerate(warnings)]

    data = payload.get("data", {})
    if len(json.dumps(data, ensure_ascii=False)) > 64 * 1024:
        raise ContractError("data exceeds 64 KiB")

    if status in {"SUCCESS", "PARTIAL", "CONFLICT"} and data not in ({}, None, []) and not normalized_evidence:
        raise ContractError(f"{status} with asserted data requires evidence")
    if status == "NO_DATA" and data not in ({}, None, []):
        raise ContractError("NO_DATA must not assert data")

    return ResearchOutput(
        status=status,
        data=data,
        evidence=normalized_evidence,
        confidence=confidence,
        warnings=normalized_warnings,
    )
