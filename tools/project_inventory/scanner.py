from __future__ import annotations

import json
import os
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

LANG_BY_SUFFIX = {
    ".py": "Python", ".go": "Go", ".tf": "Terraform", ".hcl": "HCL",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript",
    ".jsx": "JavaScript", ".rs": "Rust", ".java": "Java", ".php": "PHP",
    ".rb": "Ruby", ".sh": "Shell", ".zsh": "Shell", ".fish": "Fish",
    ".sql": "SQL", ".yaml": "YAML", ".yml": "YAML", ".json": "JSON",
    ".toml": "TOML", ".md": "Markdown", ".proto": "Protocol Buffers",
}
IGNORE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "vendor", "dist", "build",
    ".next", ".terraform", ".cache", "target",
}
MANIFESTS = {
    "pyproject.toml", "requirements.txt", "poetry.lock", "uv.lock", "go.mod",
    "go.sum", "package.json", "pnpm-lock.yaml", "yarn.lock", "package-lock.json",
    "Cargo.toml", "composer.json", "Dockerfile", "docker-compose.yml",
    "docker-compose.yaml", "terragrunt.hcl", "Chart.yaml", "justfile",
    "Makefile", "Taskfile.yml",
}
AWS_HINTS = {
    "eks": "EKS", "ecr": "ECR", "cloudfront": "CloudFront", "waf": "WAF",
    "route53": "Route53", "aurora": "Aurora", "rds": "RDS", "lambda": "Lambda",
    "eventbridge": "EventBridge", "stepfunctions": "Step Functions",
    "step_function": "Step Functions", "batch": "Batch", "s3": "S3", "kms": "KMS",
    "sqs": "SQS", "sns": "SNS", "dynamodb": "DynamoDB",
    "cloudwatch": "CloudWatch", "secretsmanager": "Secrets Manager",
    "secrets_manager": "Secrets Manager", "ssm": "SSM",
    "elasticache": "ElastiCache", "opensearch": "OpenSearch",
    "api_gateway": "API Gateway",
}
DATA_STORE_SERVICES = {"Aurora", "RDS", "DynamoDB", "ElastiCache", "OpenSearch", "S3"}
INTERFACE_PATTERNS = {
    "openapi": ("http-api", re.compile(r"(?:^|/)(?:openapi|swagger)[^/]*\.(?:ya?ml|json)$", re.I)),
    "protobuf": ("grpc/protobuf", re.compile(r"\.proto$", re.I)),
    "graphql": ("graphql", re.compile(r"(?:^|/)[^/]*\.graphqls?$", re.I)),
}

@dataclass
class ScanOptions:
    max_files_per_project: int = 6000
    content_probe_bytes: int = 12000


def _git(path: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), *args],
            capture_output=True, text=True, timeout=3, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = result.stdout.strip()
    return value or None


def _iter_files(root: Path, limit: int) -> Iterable[Path]:
    count = 0
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for filename in files:
            if count >= limit:
                return
            count += 1
            yield Path(current) / filename


def _safe_probe(path: Path, max_bytes: int) -> str:
    try:
        data = path.read_bytes()[:max_bytes]
    except (OSError, PermissionError):
        return ""
    if b"\x00" in data:
        return ""
    return data.decode("utf-8", errors="ignore")


def _line_number(text: str, needle: str) -> int | None:
    low = needle.lower()
    for index, line in enumerate(text.splitlines(), 1):
        if low in line.lower():
            return index
    return None


def _component_type(manifests: set[str], iac: set[str], containers: set[str]) -> str:
    names = {Path(m).name for m in manifests}
    if iac and not ({"go.mod", "pyproject.toml", "package.json"} & names):
        return "infrastructure"
    if containers or {"go.mod", "pyproject.toml", "package.json"} & names:
        return "service-or-application"
    if manifests:
        return "library-or-application"
    return "unknown"


def scan_project(path: Path, options: ScanOptions | None = None) -> dict:
    options = options or ScanOptions()
    languages: Counter[str] = Counter()
    manifests: set[str] = set()
    iac: set[str] = set()
    ci: set[str] = set()
    containers: set[str] = set()
    kubernetes: set[str] = set()
    aws_services: set[str] = set()
    evidence: list[dict] = []
    interfaces: list[dict] = []
    service_evidence: dict[str, list[str]] = {}

    for file_path in _iter_files(path, options.max_files_per_project):
        rel = file_path.relative_to(path).as_posix()
        suffix = file_path.suffix.lower()
        low = rel.lower()
        if suffix in LANG_BY_SUFFIX:
            languages[LANG_BY_SUFFIX[suffix]] += 1
        if file_path.name in MANIFESTS:
            manifests.add(rel)
        if suffix == ".tf" or "terragrunt" in low or "terraform" in low:
            iac.add(rel)
        if ".github/workflows/" in low or "/.gitlab-ci" in low or "codefresh" in low:
            ci.add(rel)
        if file_path.name.lower().startswith("dockerfile") or "docker-compose" in low:
            containers.add(rel)
        if "/charts/" in f"/{low}" or "/helm/" in f"/{low}" or "k8s" in low or "kubernetes" in low or file_path.name == "Chart.yaml":
            kubernetes.add(rel)

        for _, (interface_type, pattern) in INTERFACE_PATTERNS.items():
            if pattern.search(rel):
                entry = {"type": interface_type, "name": Path(rel).name, "confidence": "high", "evidence": [rel]}
                if entry not in interfaces:
                    interfaces.append(entry)
                evidence.append({"kind": "interface", "value": interface_type, "file": rel, "line": None, "confidence": "high"})

        if suffix in {".tf", ".hcl", ".yaml", ".yml", ".json", ".py", ".go", ".ts", ".js"}:
            text = _safe_probe(file_path, options.content_probe_bytes)
            low_text = text.lower()
            for needle, service in AWS_HINTS.items():
                if needle in low_text:
                    aws_services.add(service)
                    line = _line_number(text, needle)
                    marker = f"{rel}:{line}" if line else rel
                    service_evidence.setdefault(service, [])
                    if marker not in service_evidence[service]:
                        service_evidence[service].append(marker)
                    evidence.append({"kind": "aws_service", "value": service, "file": rel, "line": line, "confidence": "medium"})

    component_type = _component_type(manifests, iac, containers)
    components = [{"id": path.name, "type": component_type, "confidence": "medium" if component_type != "unknown" else "low", "evidence": sorted(manifests)[:12]}]
    resources = [{"kind": "aws-service", "name": service, "confidence": "medium", "evidence": service_evidence.get(service, [])[:12]} for service in sorted(aws_services)]
    data_stores = [{"kind": service, "confidence": "medium", "evidence": service_evidence.get(service, [])[:12]} for service in sorted(aws_services & DATA_STORE_SERVICES)]

    return {
        "name": path.name,
        "path": str(path.resolve()),
        "git": {"branch": _git(path, "rev-parse", "--abbrev-ref", "HEAD"), "remote": _git(path, "remote", "get-url", "origin"), "head": _git(path, "rev-parse", "HEAD")},
        "languages": dict(languages.most_common()),
        "manifests": sorted(manifests),
        "components": components,
        "interfaces": sorted(interfaces, key=lambda x: (x["type"], x.get("name", ""))),
        "resources": resources,
        "data_stores": data_stores,
        "signals": {"iac": sorted(iac), "ci": sorted(ci), "containers": sorted(containers), "kubernetes": sorted(kubernetes), "aws_services": sorted(aws_services)},
        "evidence": evidence,
    }


def discover_projects(root: Path) -> list[Path]:
    root = root.expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Projects root does not exist or is not a directory: {root}")
    return [child for child in sorted(root.iterdir()) if child.is_dir() and not child.name.startswith(".")]


def _infer_relationships(projects: list[dict]) -> list[dict]:
    """Infer only high-signal repository relationships from explicit project-name references."""
    names = {p["name"] for p in projects if p.get("name")}
    relationships: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for project in projects:
        source = project["name"]
        remote = (project.get("git") or {}).get("remote") or ""
        for target in names - {source}:
            if target.lower() in remote.lower():
                key = (source, target, "repository-reference")
                if key not in seen:
                    seen.add(key)
                    relationships.append({
                        "source": source,
                        "target": target,
                        "type": "repository-reference",
                        "protocol": None,
                        "confidence": "low",
                        "evidence": [{"project": source, "file": ".git/config", "line": None, "detail": "Target project name appears in git remote; validate before using as an architecture edge."}],
                    })
    return relationships


def scan_roots(roots: list[Path], options: ScanOptions | None = None) -> dict:
    projects: list[dict] = []
    normalized_roots: list[str] = []
    for root in roots:
        root = root.expanduser().resolve()
        normalized_roots.append(str(root))
        projects.extend(scan_project(project, options) for project in discover_projects(root))
    return {"version": "2.0", "generated_at": datetime.now(timezone.utc).isoformat(), "roots": normalized_roots, "projects": projects, "relationships": _infer_relationships(projects)}


def to_json(data: dict) -> str:
    return json.dumps(data, indent=2, sort_keys=False)
