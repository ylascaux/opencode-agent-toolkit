from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from scanner import ScanOptions, scan_roots

app = FastAPI(title="OpenCode Project Inventory API", version="1.0.0")


class ScanRequest(BaseModel):
    roots: list[str] | None = None
    max_files_per_project: int = Field(default=6000, ge=100, le=50000)


def _allowed_root() -> Path:
    return Path(os.environ.get("PROJECTS_ROOT", "~/Projects")).expanduser().resolve()


def _validate_roots(raw_roots: list[str] | None) -> list[Path]:
    allowed = _allowed_root()
    requested = [allowed] if not raw_roots else [Path(x).expanduser().resolve() for x in raw_roots]
    for root in requested:
        if root != allowed and allowed not in root.parents:
            raise HTTPException(status_code=403, detail=f"Root must be inside PROJECTS_ROOT ({allowed})")
    return requested


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/scan")
def scan(request: ScanRequest) -> dict:
    try:
        return scan_roots(_validate_roots(request.roots), ScanOptions(max_files_per_project=request.max_files_per_project))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
