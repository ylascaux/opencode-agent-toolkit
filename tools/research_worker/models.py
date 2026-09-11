from __future__ import annotations

from typing import Any, Literal
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

FORBIDDEN_REMOTE_KEYS = {
    "model", "provider", "agent", "prompt", "temperature", "reasoning_effort",
    "reasoning", "thinking", "command", "shell", "callback_url", "local_path",
    "repository_path", "tool", "opencode", "opencode_config", "server", "attach",
}


def _normalized_key(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def reject_top_level_remote_control_fields(value: Any) -> None:
    if not isinstance(value, dict):
        return
    for key in value:
        key_string = str(key)
        if _normalized_key(key_string) in FORBIDDEN_REMOTE_KEYS:
            raise ValueError(f"Remote execution-control field is forbidden at job.{key_string}")


class Subject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1, max_length=80)
    id: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, min_length=1, max_length=240)
    label: str | None = Field(default=None, min_length=1, max_length=300)


class Lease(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generation: int = Field(ge=1)
    expires_at: str = Field(min_length=1, max_length=80)


class ExternalResearchJob(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(validation_alias=AliasChoices("id", "job_id"), min_length=1, max_length=200)
    job_type: str = Field(min_length=1, max_length=120)
    subject: Subject
    requested_fields: list[str] = Field(min_length=1, max_length=64)
    requirements: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    result_schema: dict[str, Any] | None = None
    schema_version: str = Field(default="1", min_length=1, max_length=40)
    lease: Lease

    @model_validator(mode="before")
    @classmethod
    def reject_execution_control(cls, value: Any) -> Any:
        # Only the transport envelope can control execution. Nested subject/context/schema
        # values are untrusted domain data and may legitimately contain words such as
        # "model" or "provider"; the local protocol never interprets them as controls.
        reject_top_level_remote_control_fields(value)
        return value

    @model_validator(mode="after")
    def unique_requested_fields(self) -> "ExternalResearchJob":
        if len(set(self.requested_fields)) != len(self.requested_fields):
            raise ValueError("requested_fields must be unique")
        return self


class ClaimResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs: list[ExternalResearchJob] = Field(default_factory=list, max_length=32)


ResearchStatus = Literal["complete", "partial", "blocked", "failed", "escalation_required"]
Confidence = Literal["high", "medium", "low"]
Tier = Literal["low", "medium", "high"]
ExternalStatus = Literal["SUCCESS", "PARTIAL", "NO_DATA", "CONFLICT", "FAILED"]
ExternalConfidence = Literal["HIGH", "MEDIUM", "LOW"]


class ToolkitEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["url", "file", "api", "search_result", "log", "metric", "trace", "runtime_check", "other"]
    status: Literal["verified", "partially_verified", "unverified", "contradicted"]
    source: str = Field(min_length=1, max_length=4000)
    result: str = Field(max_length=8000)
    retrieved_at: str | None = Field(default=None, max_length=80)


class Execution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: str = Field(min_length=1, max_length=120)
    tier: Tier
    model: str | None = Field(default=None, max_length=240)
    attempts: int = Field(ge=1, le=20)
    duration_ms: int | None = Field(default=None, ge=0)


class Escalation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required: bool
    reason: str | None = Field(default=None, max_length=4000)
    next_tier: Literal["medium", "high"] | None = None
    next_agent: str | None = Field(default=None, max_length=120)


class ToolkitResearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"]
    job_id: str = Field(min_length=1, max_length=200)
    stage: Literal["pipeline", "source_discovery", "structured_extraction", "entity_resolution", "evidence_audit", "deep_reasoning"]
    status: ResearchStatus
    confidence: Confidence
    confidence_reason: str | None = Field(default=None, max_length=4000)
    data: Any
    evidence: list[ToolkitEvidence] = Field(max_length=100)
    issues: list[str] = Field(max_length=100)
    execution: Execution
    escalation: Escalation | None = None

    @model_validator(mode="after")
    def evidence_for_assertions(self) -> "ToolkitResearchResult":
        asserted = self.data not in ({}, [], None, "")
        if asserted and self.status in {"complete", "partial"} and not self.evidence:
            raise ValueError("complete/partial asserted data requires evidence")
        return self


class ResultSubmission(BaseModel):
    """Caller-facing result envelope. Provider/model/agent details stay local to the toolkit."""

    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1, max_length=200)
    result_id: str = Field(min_length=1, max_length=200)
    schema_version: str = Field(min_length=1, max_length=40)
    status: ExternalStatus
    data: Any
    evidence: list[ToolkitEvidence] = Field(max_length=100)
    confidence: ExternalConfidence
    warnings: list[str] = Field(default_factory=list, max_length=100)
    worker_id: str = Field(min_length=1, max_length=120)
    worker_version: str = Field(min_length=1, max_length=80)
    lease_generation: int = Field(ge=1)


def to_external_submission(
    result: ToolkitResearchResult,
    *,
    external_schema_version: str,
    result_id: str,
    worker_id: str,
    worker_version: str,
    lease_generation: int,
) -> ResultSubmission:
    contradicted = any(item.status == "contradicted" for item in result.evidence)
    if contradicted:
        status: ExternalStatus = "CONFLICT"
    elif result.status == "complete":
        status = "SUCCESS"
    elif result.status == "partial":
        status = "PARTIAL"
    elif result.status == "blocked":
        status = "NO_DATA" if result.data in ({}, [], None, "") else "PARTIAL"
    else:
        # Local escalation is owned by the toolkit. A final failed/escalation_required
        # status means the local pipeline could not finish the job and must not leak
        # model/agent routing instructions back to the caller.
        status = "FAILED"

    warnings = list(result.issues)
    if result.confidence_reason:
        warnings.append(result.confidence_reason)
    if result.escalation and result.escalation.reason:
        warnings.append(result.escalation.reason)
    warnings = [value[:500] for value in warnings if value.strip()][:100]

    return ResultSubmission(
        job_id=result.job_id,
        result_id=result_id,
        schema_version=external_schema_version,
        status=status,
        data={} if status == "NO_DATA" else result.data,
        evidence=result.evidence,
        confidence=result.confidence.upper(),
        warnings=warnings,
        worker_id=worker_id,
        worker_version=worker_version,
        lease_generation=lease_generation,
    )
