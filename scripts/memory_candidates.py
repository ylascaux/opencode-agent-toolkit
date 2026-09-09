#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from memory_context import MemorySettings, detect_project, ensure_memory_directory, resolve_project_id

BUCKETS = ("candidates", "accepted", "rejected", "promoted")
KINDS = ("project_fact", "decision", "convention", "known_issue", "workstyle", "hat_preference")
ALLOWED_PROJECT_TARGETS = {
    "project/context.md": "context.md",
    "project/decisions.md": "decisions.md",
    "project/conventions.md": "conventions.md",
    "project/known-issues.md": "known-issues.md",
    "project/current.md": "current.md",
}
ALLOWED_WORKSTYLE_TARGETS = {
    "workstyle/preferences.md",
    "workstyle/engineering.md",
    "workstyle/agent-collaboration.md",
    "workstyle/communication.md",
}
ID_RE = re.compile(r"^[a-f0-9]{6,64}$")
HAT_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class CandidateRef:
    bucket: str
    path: Path
    data: dict[str, Any]


def candidate_root() -> Path:
    state_home = Path(os.getenv("XDG_STATE_HOME") or (Path.home() / ".local" / "state"))
    return Path(
        os.getenv(
            "OAT_MEMORY_CANDIDATE_DIR",
            str(state_home / "opencode-agent-toolkit" / "memory"),
        )
    ).expanduser()


def load_candidate(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid memory candidate {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Memory candidate must be an object: {path}")
    return data


def candidate_files(root: Path, bucket: str) -> list[Path]:
    directory = root / bucket
    if not directory.is_dir():
        return []
    return sorted(
        (path for path in directory.glob("*.json") if path.is_file() and not path.is_symlink()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def find_candidate(root: Path, value: str, *, buckets: tuple[str, ...] = BUCKETS) -> CandidateRef:
    needle = value.strip().lower()
    if not ID_RE.fullmatch(needle):
        raise SystemExit("Candidate id must be a hexadecimal id/prefix with at least 6 characters")
    matches: list[CandidateRef] = []
    for bucket in buckets:
        for path in candidate_files(root, bucket):
            data = load_candidate(path)
            fingerprint = str(data.get("fingerprint", path.stem)).lower()
            candidate_id = str(data.get("id", "")).lower()
            if fingerprint.startswith(needle) or candidate_id.startswith(needle):
                matches.append(CandidateRef(bucket=bucket, path=path, data=data))
    if not matches:
        raise SystemExit(f"Memory candidate not found: {value}")
    if len(matches) > 1:
        locations = ", ".join(f"{ref.bucket}/{ref.path.name}" for ref in matches[:6])
        raise SystemExit(f"Candidate prefix is ambiguous: {value} ({locations})")
    return matches[0]


def _string(data: dict[str, Any], key: str, limit: int = 4000) -> str:
    value = data.get(key)
    return str(value).strip()[:limit] if value is not None else ""


def render_candidate_markdown(data: dict[str, Any], *, status: str, promoted_to: str = "") -> str:
    candidate_id = _string(data, "id", 64)
    fingerprint = _string(data, "fingerprint", 64)
    created_at = _string(data, "created_at", 80)
    project_id = _string(data, "project_id", 120)
    kind = _string(data, "kind", 60)
    confidence = _string(data, "confidence", 30)
    source = _string(data, "source", 80)
    session_id = _string(data, "session_id", 160)
    occurrences = int(data.get("occurrences", 1) or 1)
    last_seen_at = _string(data, "last_seen_at", 80) or created_at
    title = _string(data, "title", 180) or "Untitled memory candidate"
    statement = _string(data, "statement", 4000)
    rationale = _string(data, "rationale", 2000)
    target = _string(data, "suggested_target", 240)
    hats = data.get("hats") if isinstance(data.get("hats"), list) else []

    frontmatter = [
        "---",
        f"id: {candidate_id}",
        f"fingerprint: {fingerprint}",
        f"status: {status}",
        f"kind: {kind}",
        f"confidence: {confidence}",
        f"project: {project_id or 'global'}",
        f"created_at: {created_at}",
        f"source: {source}",
        f"occurrences: {occurrences}",
        f"last_seen_at: {last_seen_at}",
    ]
    if session_id:
        frontmatter.append(f"session_id: {session_id}")
    if target:
        frontmatter.append(f"suggested_target: {target}")
    if promoted_to:
        frontmatter.append(f"promoted_to: {promoted_to}")
    if hats:
        frontmatter.append("hats: [" + ", ".join(str(value) for value in hats[:8]) + "]")
    frontmatter.append("---")

    body = [*frontmatter, "", f"# {title}", "", statement]
    if rationale:
        body.extend(["", "## Rationale", "", rationale])
    body.extend(
        [
            "",
            "## Provenance",
            "",
            "This is a curated memory candidate extracted from an OpenCode session. The raw transcript is not stored here.",
        ]
    )
    return "\n".join(body).rstrip() + "\n"


def resolve_target(vault: Path, data: dict[str, Any], requested: str = "") -> tuple[str, Path]:
    target = requested.strip() or _string(data, "suggested_target", 240)
    project_id = _string(data, "project_id", 120)
    if target in ALLOWED_PROJECT_TARGETS:
        if not project_id or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", project_id):
            raise SystemExit("Project-scoped promotion requires a valid candidate project_id")
        relative = Path("projects") / project_id / ALLOWED_PROJECT_TARGETS[target]
    elif target in ALLOWED_WORKSTYLE_TARGETS:
        relative = Path(target)
    elif target.startswith("hat:"):
        hat = target.split(":", 1)[1].removesuffix(".md")
        if not HAT_RE.fullmatch(hat):
            raise SystemExit(f"Invalid hat target: {target}")
        relative = Path("hats") / f"{hat}.md"
        target = f"hat:{hat}"
    else:
        allowed = sorted(ALLOWED_PROJECT_TARGETS | ALLOWED_WORKSTYLE_TARGETS)
        raise SystemExit(
            f"Unsupported promotion target {target!r}. Use one of {', '.join(allowed)} or hat:<name>."
        )
    absolute = (vault / relative).resolve()
    try:
        absolute.relative_to(vault.resolve())
    except ValueError as exc:
        raise SystemExit("Promotion target escapes the memory vault") from exc
    if absolute.is_symlink():
        raise SystemExit("Refusing to promote into a symlink")
    return target, absolute


def learned_bullet(data: dict[str, Any]) -> str:
    title = _string(data, "title", 180) or "Memory"
    statement = _string(data, "statement", 4000)
    rationale = _string(data, "rationale", 1200)
    suffix = f" — {rationale}" if rationale else ""
    return f"- **{title}** — {statement}{suffix}"


def append_learned(path: Path, data: dict[str, Any]) -> bool:
    bullet = learned_bullet(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    current = path.read_text() if path.exists() else f"# {path.stem.replace('-', ' ').title()}\n"
    if _string(data, "statement", 4000) in current:
        return False
    marker = "## Learned memory"
    if marker not in current:
        current = current.rstrip() + f"\n\n{marker}\n"
    path.write_text(current.rstrip() + "\n\n" + bullet + "\n")
    return True


def _git(vault: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
    result = subprocess.run(
        ["git", "-C", str(vault), *args],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"git exited {result.returncode}"
        raise SystemExit(f"Memory Git operation failed: {detail}")
    return result


def require_clean(vault: Path) -> None:
    result = _git(vault, "status", "--porcelain")
    if result.stdout.strip():
        raise SystemExit("Memory repository has uncommitted changes; resolve them before accepting/promoting candidates")


def commit_paths(vault: Path, message: str, paths: list[Path]) -> None:
    relatives = [str(path.resolve().relative_to(vault.resolve())) for path in paths]
    _git(vault, "add", "--", *relatives)
    result = _git(vault, "diff", "--cached", "--quiet", check=False)
    if result.returncode == 0:
        return
    if result.returncode != 1:
        raise SystemExit("Unable to inspect staged memory changes")
    _git(vault, "commit", "-m", message, "--", *relatives)


def move_local(ref: CandidateRef, bucket: str, data: dict[str, Any] | None = None) -> Path:
    destination_dir = ref.path.parents[1] / bucket
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / ref.path.name
    ref.path.replace(destination)
    if data is not None:
        destination.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        try:
            destination.chmod(0o600)
        except OSError:
            pass
    return destination


def ensure_vault() -> Path:
    settings = MemorySettings.from_env(enabled_override=True)
    vault = ensure_memory_directory(settings, force_sync=True)
    if vault is None:
        raise SystemExit("Memory repository is unavailable")
    if not (vault / ".git").is_dir():
        raise SystemExit("Candidate acceptance/promotion requires a Git-backed memory directory")
    return vault


def ensure_candidate_project(data: dict[str, Any], vault: Path) -> dict[str, Any]:
    if _string(data, "project_id", 120):
        return data
    identity = detect_project(Path.cwd())
    project_id = resolve_project_id(vault, identity, override=os.getenv("OAT_MEMORY_PROJECT", ""))
    if not project_id:
        return data
    return {**data, "project_id": project_id, "project_name": identity.name}


def cmd_add(args: argparse.Namespace) -> int:
    root = candidate_root()
    project_id = args.project.strip()
    if not project_id and args.kind in {"project_fact", "decision", "convention", "known_issue"}:
        vault = ensure_vault()
        identity = detect_project(Path.cwd())
        project_id = resolve_project_id(vault, identity, override=os.getenv("OAT_MEMORY_PROJECT", ""))
        if not project_id:
            raise SystemExit("Could not resolve a memory project; pass --project explicitly")
    title = args.title.strip()
    statement = args.statement.strip()
    stable = "\n".join([project_id, args.kind, title.lower(), statement.lower()])
    fingerprint = hashlib.sha256(stable.encode()).hexdigest()
    for bucket in BUCKETS:
        if (root / bucket / f"{fingerprint}.json").exists():
            print(f"duplicate={fingerprint[:12]} bucket={bucket}")
            return 0
    data = {
        "id": fingerprint[:12],
        "fingerprint": fingerprint,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "session_id": "",
        "project_id": project_id,
        "project_name": Path.cwd().name,
        "kind": args.kind,
        "title": title,
        "statement": statement,
        "rationale": args.rationale.strip(),
        "confidence": args.confidence,
        "suggested_target": args.target.strip(),
        "source": "manual-cli",
        "extractor_model": "none",
        "occurrences": 1,
        "last_seen_at": datetime.now(timezone.utc).isoformat(),
    }
    directory = root / "candidates"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{fingerprint}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    print(f"candidate={data['id']} path={path}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    root = candidate_root()
    buckets = BUCKETS if args.all else (args.status,)
    found = 0
    for bucket in buckets:
        for path in candidate_files(root, bucket):
            data = load_candidate(path)
            found += 1
            print(
                f"{_string(data, 'id', 20):12} {bucket:10} {_string(data, 'confidence', 12):6} "
                f"{_string(data, 'kind', 18):18} {_string(data, 'project_id', 24) or '-':24} {_string(data, 'title', 100)}"
            )
    if not found:
        print("No memory candidates.")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    ref = find_candidate(candidate_root(), args.id)
    print(json.dumps(ref.data, indent=2, ensure_ascii=False))
    return 0


def cmd_reject(args: argparse.Namespace) -> int:
    ref = find_candidate(candidate_root(), args.id, buckets=("candidates",))
    now = datetime.now(timezone.utc).isoformat()
    data = {**ref.data, "status": "rejected", "rejected_at": now}
    destination = move_local(ref, "rejected", data)
    print(f"rejected={_string(ref.data, 'id', 20)} path={destination}")
    return 0


def cmd_accept(args: argparse.Namespace) -> int:
    ref = find_candidate(candidate_root(), args.id, buckets=("candidates",))
    vault = ensure_vault()
    require_clean(vault)
    data = ensure_candidate_project(ref.data, vault)
    now = datetime.now(timezone.utc).isoformat()
    data = {**data, "status": "accepted", "accepted_at": now}
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    candidate_id = _string(data, "id", 20) or ref.path.stem[:12]
    destination = vault / "inbox" / "accepted" / f"{stamp}-{candidate_id}.md"
    if destination.exists():
        raise SystemExit(f"Accepted candidate already exists in memory repository: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_candidate_markdown(data, status="accepted"))
    try:
        commit_paths(vault, f"memory: accept {candidate_id}", [destination])
    except BaseException:
        destination.unlink(missing_ok=True)
        _git(vault, "reset", "-q", "--", str(destination.relative_to(vault)), check=False)
        raise
    move_local(ref, "accepted", data)
    if args.push:
        _git(vault, "push")
    print(f"accepted={candidate_id} memory={destination.relative_to(vault)} pushed={'yes' if args.push else 'no'}")
    return 0


def find_accepted_markdown(vault: Path, candidate_id: str) -> Path:
    directory = vault / "inbox" / "accepted"
    matches = list(directory.glob(f"*-{candidate_id}.md")) if directory.is_dir() else []
    if len(matches) != 1:
        raise SystemExit(f"Expected one accepted memory note for {candidate_id}, found {len(matches)}")
    return matches[0]


def cmd_promote(args: argparse.Namespace) -> int:
    ref = find_candidate(candidate_root(), args.id, buckets=("accepted",))
    vault = ensure_vault()
    require_clean(vault)
    data = ensure_candidate_project(ref.data, vault)
    target_name, target_path = resolve_target(vault, data, args.target)
    accepted = find_accepted_markdown(vault, _string(data, "id", 20))
    promoted_dir = vault / "inbox" / "promoted"
    promoted_dir.mkdir(parents=True, exist_ok=True)
    promoted_note = promoted_dir / accepted.name
    if promoted_note.exists():
        raise SystemExit(f"Promoted note already exists: {promoted_note}")

    now = datetime.now(timezone.utc).isoformat()
    promoted_data = {**data, "status": "promoted", "promoted_at": now, "promoted_to": target_name}
    target_before = target_path.read_text() if target_path.exists() else None
    changed = append_learned(target_path, promoted_data)
    accepted_before = accepted.read_text()
    accepted.replace(promoted_note)
    promoted_note.write_text(render_candidate_markdown(promoted_data, status="promoted", promoted_to=target_name))
    try:
        commit_paths(
            vault,
            f"memory: promote {_string(promoted_data, 'id', 20)} to {target_name}",
            [target_path, accepted, promoted_note],
        )
    except BaseException:
        if target_before is None:
            target_path.unlink(missing_ok=True)
        else:
            target_path.write_text(target_before)
        promoted_note.unlink(missing_ok=True)
        accepted.parent.mkdir(parents=True, exist_ok=True)
        accepted.write_text(accepted_before)
        _git(vault, "reset", "-q", check=False)
        raise
    move_local(ref, "promoted", promoted_data)
    if args.push:
        _git(vault, "push")
    print(
        f"promoted={_string(promoted_data, 'id', 20)} target={target_name} changed={'yes' if changed else 'no'} "
        f"pushed={'yes' if args.push else 'no'}"
    )
    return 0


def cmd_push(_args: argparse.Namespace) -> int:
    vault = ensure_vault()
    require_clean(vault)
    _git(vault, "push")
    print("memory pushed")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Review and curate local OpenCode memory candidates.")
    sub = result.add_subparsers(dest="command", required=True)

    manual = sub.add_parser("add")
    manual.add_argument("kind", choices=KINDS)
    manual.add_argument("title")
    manual.add_argument("statement")
    manual.add_argument("--rationale", default="")
    manual.add_argument("--confidence", choices=("medium", "high"), default="high")
    manual.add_argument("--target", default="")
    manual.add_argument("--project", default="")
    manual.set_defaults(func=cmd_add)

    listing = sub.add_parser("list")
    listing.add_argument("--status", choices=BUCKETS, default="candidates")
    listing.add_argument("--all", action="store_true")
    listing.set_defaults(func=cmd_list)

    show = sub.add_parser("show")
    show.add_argument("id")
    show.set_defaults(func=cmd_show)

    reject = sub.add_parser("reject")
    reject.add_argument("id")
    reject.set_defaults(func=cmd_reject)

    accept = sub.add_parser("accept")
    accept.add_argument("id")
    accept.add_argument("--push", action="store_true")
    accept.set_defaults(func=cmd_accept)

    promote = sub.add_parser("promote")
    promote.add_argument("id")
    promote.add_argument("target", nargs="?", default="")
    promote.add_argument("--push", action="store_true")
    promote.set_defaults(func=cmd_promote)

    publish = sub.add_parser("push")
    publish.set_defaults(func=cmd_push)
    return result


def main() -> int:
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
