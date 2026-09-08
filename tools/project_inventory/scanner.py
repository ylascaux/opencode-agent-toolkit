from __future__ import annotations

import json
import os
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

LANG_BY_SUFFIX = {".py":"Python",".go":"Go",".tf":"Terraform",".hcl":"HCL",".ts":"TypeScript",".tsx":"TypeScript",".js":"JavaScript",".jsx":"JavaScript",".rs":"Rust",".java":"Java",".php":"PHP",".rb":"Ruby",".sh":"Shell",".zsh":"Shell",".fish":"Fish",".sql":"SQL",".yaml":"YAML",".yml":"YAML",".json":"JSON",".toml":"TOML",".md":"Markdown"}
IGNORE_DIRS = {".git",".venv","venv","node_modules","vendor","dist","build",".next",".terraform",".cache","target"}
MANIFESTS = {"pyproject.toml","requirements.txt","poetry.lock","uv.lock","go.mod","go.sum","package.json","pnpm-lock.yaml","yarn.lock","package-lock.json","Cargo.toml","composer.json","Dockerfile","docker-compose.yml","docker-compose.yaml","terragrunt.hcl","Chart.yaml","Makefile","Taskfile.yml"}
AWS_HINTS = {"eks":"EKS","ecr":"ECR","cloudfront":"CloudFront","waf":"WAF","route53":"Route53","aurora":"Aurora","rds":"RDS","lambda":"Lambda","eventbridge":"EventBridge","stepfunctions":"Step Functions","step_function":"Step Functions","batch":"Batch","s3":"S3","kms":"KMS","sqs":"SQS","sns":"SNS","dynamodb":"DynamoDB","cloudwatch":"CloudWatch","secretsmanager":"Secrets Manager","secrets_manager":"Secrets Manager","ssm":"SSM","elasticache":"ElastiCache","opensearch":"OpenSearch","api_gateway":"API Gateway"}

@dataclass
class ScanOptions:
    max_files_per_project: int = 6000
    content_probe_bytes: int = 12000


def _git(path: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(["git","-C",str(path),*args],capture_output=True,text=True,timeout=3,check=False)
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
    return data.decode("utf-8", errors="ignore").lower()


def scan_project(path: Path, options: ScanOptions | None = None) -> dict:
    options = options or ScanOptions()
    languages: Counter[str] = Counter(); manifests=[]; iac=set(); ci=set(); containers=set(); kubernetes=set(); aws_services=set()
    for file_path in _iter_files(path, options.max_files_per_project):
        rel=file_path.relative_to(path).as_posix(); suffix=file_path.suffix.lower(); low=rel.lower()
        if suffix in LANG_BY_SUFFIX: languages[LANG_BY_SUFFIX[suffix]] += 1
        if file_path.name in MANIFESTS: manifests.append(rel)
        if suffix == ".tf" or "terragrunt" in low or "terraform" in low: iac.add(rel)
        if ".github/workflows/" in low or "/.gitlab-ci" in low or "codefresh" in low: ci.add(rel)
        if file_path.name.lower().startswith("dockerfile") or "docker-compose" in low: containers.add(rel)
        if "/charts/" in f"/{low}" or "/helm/" in f"/{low}" or "k8s" in low or "kubernetes" in low or file_path.name == "Chart.yaml": kubernetes.add(rel)
        if suffix in {".tf",".hcl",".yaml",".yml",".json",".py",".go",".ts",".js"}:
            text=_safe_probe(file_path, options.content_probe_bytes)
            for needle, service in AWS_HINTS.items():
                if needle in text: aws_services.add(service)
    return {"name":path.name,"path":str(path.resolve()),"git":{"branch":_git(path,"rev-parse","--abbrev-ref","HEAD"),"remote":_git(path,"remote","get-url","origin"),"head":_git(path,"rev-parse","HEAD")},"languages":dict(languages.most_common()),"manifests":sorted(set(manifests)),"signals":{"iac":sorted(iac),"ci":sorted(ci),"containers":sorted(containers),"kubernetes":sorted(kubernetes),"aws_services":sorted(aws_services)}}


def discover_projects(root: Path) -> list[Path]:
    root=root.expanduser().resolve()
    if not root.exists() or not root.is_dir(): raise FileNotFoundError(f"Projects root does not exist or is not a directory: {root}")
    return [child for child in sorted(root.iterdir()) if child.is_dir() and not child.name.startswith(".")]


def scan_roots(roots: list[Path], options: ScanOptions | None = None) -> dict:
    projects=[]; normalized_roots=[]
    for root in roots:
        root=root.expanduser().resolve(); normalized_roots.append(str(root)); projects.extend(scan_project(project,options) for project in discover_projects(root))
    return {"version":"1.0","generated_at":datetime.now(timezone.utc).isoformat(),"roots":normalized_roots,"projects":projects}


def to_json(data: dict) -> str:
    return json.dumps(data, indent=2, sort_keys=False)
