from __future__ import annotations

from typing import Any

from .contracts import (
    DISCOVERY_PAYLOAD_SCHEMA,
    RESULT_SCHEMA,
    ResearchWorkerError,
    source_constraint_errors,
    tier_model,
    tier_rank,
    validate_candidate,
    validate_job,
    validation_errors,
)
from .opencode import discovery_prompt, extraction_prompt


class ResearchPipeline:
    def __init__(self, runner: Any, *, max_tier: str = "high", schema_retries: int = 1):
        if max_tier not in {"low", "medium", "high"}:
            raise ResearchWorkerError("max_tier must be low, medium, or high")
        if schema_retries < 0 or schema_retries > 3:
            raise ResearchWorkerError("schema_retries must be between 0 and 3")
        self.runner = runner
        self.max_tier = max_tier
        self.schema_retries = schema_retries

    def _call(
        self,
        attempts: list[dict[str, str]],
        *,
        agent: str,
        tier: str,
        prompt: str,
        reason: str,
        force_tier_model: bool,
    ) -> dict[str, Any]:
        model = tier_model(tier) if force_tier_model else None
        try:
            candidate = self.runner.run(agent, prompt, model=model)
        except Exception as exc:
            attempts.append({"agent": agent, "tier": tier, "status": "error", "reason": f"{reason}: {exc}"})
            raise ResearchWorkerError(str(exc)) from exc

        errors = validate_candidate(candidate)
        attempts.append(
            {
                "agent": agent,
                "tier": tier,
                "status": "invalid" if errors else "complete",
                "reason": reason if not errors else f"{reason}; " + "; ".join(errors),
            }
        )
        if errors:
            raise ResearchWorkerError("Invalid machine candidate: " + "; ".join(errors))
        return candidate

    @staticmethod
    def _needs_escalation(candidate: dict[str, Any], payload_errors: list[str]) -> bool:
        trigger_flags = {
            "conflicting_evidence",
            "entity_ambiguity",
            "insufficient_evidence",
            "stale_evidence",
            "source_quality",
        }
        return bool(
            payload_errors
            or candidate.get("confidence") == "low"
            or set(candidate.get("flags", [])) & trigger_flags
        )

    def _discover(self, job: dict[str, Any], attempts: list[dict[str, str]]) -> dict[str, Any]:
        feedback: list[str] = []
        candidate: dict[str, Any] | None = None

        for retry in range(self.schema_retries + 1):
            try:
                candidate = self._call(
                    attempts,
                    agent="source-discovery",
                    tier="low",
                    prompt=discovery_prompt(job, feedback or None),
                    reason="initial discovery" if retry == 0 else f"discovery schema retry {retry}",
                    force_tier_model=False,
                )
            except ResearchWorkerError as exc:
                feedback = [str(exc)]
                continue
            errors = validation_errors(DISCOVERY_PAYLOAD_SCHEMA, candidate["payload"])
            if not errors:
                urls = [item["url"] for item in candidate["payload"].get("sources", [])]
                errors.extend(source_constraint_errors(job, urls))
            if not errors and not self._needs_escalation(candidate, []):
                return candidate
            feedback = errors or list(candidate.get("flags", [])) or ["source discovery returned low confidence"]

        for tier in ("medium", "high"):
            if tier_rank(self.max_tier) < tier_rank(tier):
                break
            candidate = self._call(
                attempts,
                agent="source-discovery",
                tier=tier,
                prompt=discovery_prompt(job, feedback),
                reason=f"{tier} discovery escalation",
                force_tier_model=True,
            )
            errors = validation_errors(DISCOVERY_PAYLOAD_SCHEMA, candidate["payload"])
            if not errors:
                urls = [item["url"] for item in candidate["payload"].get("sources", [])]
                errors.extend(source_constraint_errors(job, urls))
            if not errors and not self._needs_escalation(candidate, []):
                return candidate
            feedback = errors or list(candidate.get("flags", [])) or ["source discovery remained low confidence"]

        if candidate is None:
            raise ResearchWorkerError("Source discovery produced no candidate")
        return candidate

    def run(self, job: dict[str, Any]) -> dict[str, Any]:
        validate_job(job)
        attempts: list[dict[str, str]] = []
        errors: list[str] = []
        warnings: list[str] = []
        research_sources: list[Any] = list(job.get("source_hints", []))

        try:
            if job["task_type"] in {"research", "discover_sources"}:
                discovery = self._discover(job, attempts)
                warnings.extend(discovery.get("warnings", []))
                if job["task_type"] == "discover_sources":
                    candidate = discovery
                else:
                    research_sources = discovery["payload"].get("sources", [])
                    candidate = self._call(
                        attempts,
                        agent="structured-extractor",
                        tier="low",
                        prompt=extraction_prompt(job, research_sources),
                        reason="initial structured extraction",
                        force_tier_model=False,
                    )
            elif job["task_type"] == "extract":
                candidate = self._call(
                    attempts,
                    agent="structured-extractor",
                    tier="low",
                    prompt=extraction_prompt(job, research_sources),
                    reason="initial structured extraction",
                    force_tier_model=False,
                )
            else:
                raise ResearchWorkerError(f"Unsupported task_type: {job['task_type']}")
        except ResearchWorkerError as exc:
            errors.append(str(exc))
            candidate = {
                "payload": None,
                "confidence": "low",
                "evidence": [],
                "flags": ["insufficient_evidence"],
                "warnings": [],
            }

        payload_errors = validation_errors(job["output_schema"], candidate["payload"])
        if payload_errors and job["task_type"] in {"research", "extract"}:
            feedback = payload_errors
            for retry in range(self.schema_retries):
                try:
                    candidate = self._call(
                        attempts,
                        agent="structured-extractor",
                        tier="low",
                        prompt=extraction_prompt(
                            job,
                            research_sources,
                            previous=candidate,
                            feedback=feedback,
                        ),
                        reason=f"payload schema retry {retry + 1}",
                        force_tier_model=False,
                    )
                except ResearchWorkerError as exc:
                    errors.append(str(exc))
                    continue
                payload_errors = validation_errors(job["output_schema"], candidate["payload"])
                if not payload_errors:
                    break
                feedback = payload_errors

        for tier in ("medium", "high"):
            if not self._needs_escalation(candidate, payload_errors):
                break
            if tier_rank(self.max_tier) < tier_rank(tier):
                break
            try:
                candidate = self._call(
                    attempts,
                    agent="evidence-resolver",
                    tier=tier,
                    prompt=extraction_prompt(
                        job,
                        research_sources,
                        previous=candidate,
                        feedback=payload_errors or list(candidate.get("flags", [])),
                        expert=True,
                    ),
                    reason=f"{tier} evidence escalation",
                    force_tier_model=True,
                )
                payload_errors = validation_errors(job["output_schema"], candidate["payload"])
            except ResearchWorkerError as exc:
                errors.append(str(exc))

        evidence_urls = [
            item["url"]
            for item in candidate.get("evidence", [])
            if isinstance(item, dict) and isinstance(item.get("url"), str)
        ]
        payload_errors.extend(source_constraint_errors(job, evidence_urls))
        warnings.extend(candidate.get("warnings", []))
        schema_valid = not payload_errors
        unresolved = self._needs_escalation(candidate, payload_errors)

        if schema_valid and not unresolved:
            status = "complete"
        elif schema_valid:
            status = "escalation_required"
        else:
            status = "failed"
            errors.extend(payload_errors)

        result = {
            "version": "1",
            "job_id": job["job_id"],
            "status": status,
            "confidence": candidate["confidence"],
            "schema_valid": schema_valid,
            "payload": candidate["payload"],
            "evidence": candidate.get("evidence", []),
            "flags": sorted(set(candidate.get("flags", []))),
            "warnings": list(dict.fromkeys(warnings)),
            "errors": list(dict.fromkeys(errors)),
            "attempts": attempts,
        }
        result_errors = validation_errors(RESULT_SCHEMA, result)
        if result_errors:
            raise ResearchWorkerError("Internal result validation failed: " + "; ".join(result_errors))
        return result
