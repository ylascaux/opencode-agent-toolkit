"""Generic pull-based external research worker for OpenCode Agent Toolkit."""

from .contracts import ExternalResearchJob, ResearchOutput, build_toolkit_job, parse_external_job, validate_research_output

__all__ = [
    "ExternalResearchJob",
    "ResearchOutput",
    "build_toolkit_job",
    "parse_external_job",
    "validate_research_output",
]
