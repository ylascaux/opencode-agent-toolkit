from __future__ import annotations

import json
import urllib.parse
from pathlib import Path
from typing import Any

from jsonschema import FormatChecker
from jsonschema.validators import validator_for

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts"
FLAGS = {
    "conflicting_evidence",
    "entity_ambiguity",
    "insufficient_evidence",
    "stale_evidence",
    "source_quality",
}
TIERS = ("low", "medium", "high")


class ResearchWorkerError(RuntimeError):
    pass


def _load_schema(name: str) -> dict[str, Any]:
    return json.loads((CONTRACTS / name).read_text())


JOB_SCHEMA = _load_schema("research-job.schema.json")
RESULT_SCHEMA = _load_schema("research-result.schema.json")

CANDIDATE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": ["payload", "confidence", "evidence", "flags", "warnings"],
    "properties": {
        "payload": {},
        "confidence": {"enum": ["high", "medium", "low"]},
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["url"],
                "properties": {
                    "url": {"type": "string", "format": "uri"},
                    "title": {"type": "string"},
                    "source_type": {"type": "string"},
                    "claim": {"type": "string"},
                    "confidence": {"enum": ["high", "medium", "low"]},
                },
            },
        },
        "flags": {"type": "array", "uniqueItems": True, "items": {"enum": sorted(FLAGS)}},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
}

DISCOVERY_PAYLOAD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["sources"],
    "properties": {
        "sources": {
            "type": "array",
            "maxItems": 100,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["url"],
                "properties": {
                    "url": {"type": "string", "format": "uri"},
                    "title": {"type": "string"},
                    "source_type": {"type": "string"},
                    "relevance": {"enum": ["high", "medium", "low"]},
                    "authority": {"enum": ["high", "medium", "low"]},
                    "reason": {"type": "string"},
                },
            },
        }
    },
}


def validation_errors(schema: dict[str, Any], value: Any) -> list[str]:
    try:
        cls = validator_for(schema)
        cls.check_schema(schema)
        validator = cls(schema, format_checker=FormatChecker())
    except Exception as exc:
        raise ResearchWorkerError(f"Invalid JSON Schema: {exc}") from exc

    errors = sorted(validator.iter_errors(value), key=lambda item: list(item.absolute_path))
    rendered: list[str] = []
    for error in errors[:50]:
        path = ".".join(str(part) for part in error.absolute_path) or "$"
        rendered.append(f"{path}: {error.message}")
    if len(errors) > 50:
        rendered.append(f"... {len(errors) - 50} additional validation errors")
    return rendered


def _domain_matches(hostname: str, domain: str) -> bool:
    host = hostname.rstrip(".").lower()
    rule = domain.rstrip(".").lower()
    return host == rule or host.endswith("." + rule)


def source_constraint_errors(job: dict[str, Any], urls: list[str]) -> list[str]:
    constraints = job.get("constraints") or {}
    allowed = [str(item).lower() for item in constraints.get("allowed_domains", [])]
    denied = [str(item).lower() for item in constraints.get("denied_domains", [])]
    unique_urls = list(dict.fromkeys(urls))
    errors: list[str] = []

    max_sources = constraints.get("max_sources")
    if isinstance(max_sources, int) and len(unique_urls) > max_sources:
        errors.append(f"source count {len(unique_urls)} exceeds max_sources={max_sources}")

    for url in unique_urls:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            errors.append(f"unsupported source URL: {url}")
            continue
        if allowed and not any(_domain_matches(parsed.hostname, domain) for domain in allowed):
            errors.append(f"source outside allowed_domains: {url}")
        if any(_domain_matches(parsed.hostname, domain) for domain in denied):
            errors.append(f"source matches denied_domains: {url}")
    return errors


def validate_job(job: dict[str, Any]) -> None:
    errors = validation_errors(JOB_SCHEMA, job)
    if errors:
        raise ResearchWorkerError("Invalid research job: " + "; ".join(errors))
    if not isinstance(job.get("output_schema"), dict) or not job["output_schema"]:
        raise ResearchWorkerError("output_schema must be a non-empty JSON Schema object")
    try:
        validator_for(job["output_schema"]).check_schema(job["output_schema"])
    except Exception as exc:
        raise ResearchWorkerError(f"Invalid output_schema: {exc}") from exc
    source_errors = source_constraint_errors(job, list(job.get("source_hints", [])))
    if source_errors:
        raise ResearchWorkerError("Invalid source_hints: " + "; ".join(source_errors))


def validate_candidate(candidate: dict[str, Any]) -> list[str]:
    return validation_errors(CANDIDATE_SCHEMA, candidate)


def tier_rank(tier: str) -> int:
    if tier not in TIERS:
        raise ResearchWorkerError(f"Unknown tier: {tier}")
    return TIERS.index(tier)


def tier_model(tier: str) -> str:
    import os

    value = os.getenv(f"MODEL_{tier.upper()}", "").strip()
    if not value:
        raise ResearchWorkerError(f"MODEL_{tier.upper()} is not configured")
    return value
