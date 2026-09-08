# Project discovery

The toolkit can build a normalized architecture inventory from repositories under `PROJECTS_ROOT` (default `$HOME/Projects`).

## Direct agent mode

`project-scanner` is read-only and can inspect project files without modifying them:

```text
@project-scanner Inventory ~/Projects and produce architecture facts.
```

It should report facts, not inferred architecture presented as fact.

## CLI inventory

```bash
just scan
```

This writes:

```text
architecture-inventory.json
```

The inventory contains project identity, languages, manifests, infrastructure/CI/container/Kubernetes signals, detected AWS service hints and selected Git metadata. Generated/vendor/build directories are ignored.

The normalized JSON reduces repeated repository crawling and provides a stable handoff to `architecture-designer`, `platform-architect` and other specialists.

## Local API

Start the FastAPI wrapper:

```bash
just api
```

Default endpoint:

```text
POST http://127.0.0.1:8765/scan
```

The API is constrained to `PROJECTS_ROOT`; it is not intended as an arbitrary filesystem scanner.

## Typical architecture flow

```text
Projects/*
   |
   v
project-scanner / scan CLI
   |
   v
architecture-inventory.json
   |
   +--> platform-architect
   +--> architecture-designer
   +--> aws-platform
   +--> terraform-terragrunt
   +--> kubernetes
   +--> database/networking
   +--> SRE/observability/FinOps
   `--> security gates
```

Architecture outputs should explicitly distinguish facts found in the inventory from assumptions and recommendations.
