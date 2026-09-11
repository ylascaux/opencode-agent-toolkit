from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any

from .models import ToolkitResearchResult
from .protocol import render_orchestrator_prompt
from .settings import WorkerSettings

MAX_STDOUT_BYTES = 2 * 1024 * 1024
MAX_STDERR_CHARS = 4000


class ResearchExecutionError(RuntimeError):
    pass


def _candidate_payloads(stdout: str) -> list[dict[str, Any]]:
    text_events: list[str] = []
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("type") != "text":
            continue
        part = event.get("part")
        if not isinstance(part, dict) or part.get("type") != "text":
            continue
        if part.get("synthetic") is True:
            continue
        metadata = part.get("metadata")
        if isinstance(metadata, dict) and any(str(key).startswith("compaction") for key in metadata):
            continue
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            text_events.append(text.strip())

    candidates: list[str] = list(reversed(text_events))
    if text_events:
        candidates.append("\n".join(text_events))

    parsed: list[dict[str, Any]] = []
    for candidate in candidates:
        clean = candidate.strip()
        if clean.startswith("```json") and clean.endswith("```"):
            clean = clean[7:-3].strip()
        elif clean.startswith("```") and clean.endswith("```"):
            clean = clean[3:-3].strip()
        try:
            value = json.loads(clean)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            parsed.append(value)
    return parsed


def parse_opencode_result(stdout: str, expected_job_id: str) -> ToolkitResearchResult:
    if len(stdout.encode("utf-8")) > MAX_STDOUT_BYTES:
        raise ResearchExecutionError("OpenCode JSON event stream exceeds 2 MiB")
    for payload in _candidate_payloads(stdout):
        try:
            result = ToolkitResearchResult.model_validate(payload)
        except Exception:
            continue
        if result.job_id == expected_job_id:
            return result
    raise ResearchExecutionError("OpenCode did not emit a valid Research Result JSON object for the claimed job")


@dataclass
class OpenCodeExecutor:
    settings: WorkerSettings

    def execute(self, toolkit_job: dict[str, Any]) -> ToolkitResearchResult:
        prompt = render_orchestrator_prompt(toolkit_job)
        base_command = shlex.split(self.settings.opencode_command)
        if not base_command:
            raise ResearchExecutionError("OAT_RESEARCH_OPENCODE_COMMAND is empty")
        command = [
            *base_command,
            "run",
            "--agent",
            "orchestrator",
            "--format",
            "json",
            "--title",
            f"research:{toolkit_job['job_id']}",
            prompt,
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.settings.execution_timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise ResearchExecutionError("OpenCode research execution timed out") from error
        except OSError as error:
            raise ResearchExecutionError(f"Unable to start OpenCode: {error}") from error

        if completed.returncode != 0:
            stderr = completed.stderr[-MAX_STDERR_CHARS:].replace(self.settings.api_token, "[redacted]")
            raise ResearchExecutionError(f"OpenCode exited with {completed.returncode}: {stderr}")
        return parse_opencode_result(completed.stdout, str(toolkit_job["job_id"]))
