# Project discovery

The scanner reads projects under `PROJECTS_ROOT` (default `$HOME/Projects`) and writes a normalized inventory with `just scan`.

## Inventory v2

Each project contains repository/git metadata, language counts, manifests, inferred component type, detected API/interface definitions, AWS resources with evidence, data stores, IaC/CI/container/Kubernetes signals, evidence entries with file and line when available, and confidence.

Top-level `relationships` are intentionally conservative. Weak name-based heuristics stay LOW confidence; the scanner prefers an empty relationship set to a fabricated architecture edge.

Example evidence:

```json
{
  "kind": "aws_service",
  "value": "S3",
  "file": "infra/main.tf",
  "line": 42,
  "confidence": "medium"
}
```

Architecture agents validate heuristic signals before treating them as facts.

## Local API

```bash
just api
curl -sS -X POST http://127.0.0.1:8765/scan -H 'content-type: application/json' -d '{}' > architecture-inventory.json
```

The API remains constrained to the configured projects root.
