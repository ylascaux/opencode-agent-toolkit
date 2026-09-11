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


def reject_remote_control_fields(value: Any, path: str = "job") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_string = str(key)
            if _normalized_key(key_string) in FORBIDDEN_REMOTE_KEYS:
                raise ValueError(f"Remote execution-control field is forbidden at {path}.{key_string}")
            reject_remote_control_fields(item, f"{path}.{key_string}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            reject_remote_control_fields(item, f"{path}[{index}]")


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
        reject_remote_control_fields(value)
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


class ResultSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_id: str = Field(min_length=1, max_length=200)
    worker_id: str = Field(min_length=1, max_length=120)
    worker_version: str = Field(min_length=1, max_length=80)
    lease_generation: int = Field(ge=1)
    result: ToolkitResearchResult
