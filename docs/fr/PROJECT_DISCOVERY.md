# Découverte des projets

Le toolkit peut construire un inventaire d’architecture normalisé à partir des repositories présents sous `PROJECTS_ROOT` (par défaut `$HOME/Projects`).

## Mode agent direct

`project-scanner` travaille en lecture seule :

```text
@project-scanner Inventorie ~/Projects et produis des faits d’architecture.
```

L’agent doit distinguer les faits réellement trouvés des déductions.

## Inventaire CLI

```bash
just scan
```

Cette commande produit :

```text
architecture-inventory.json
```

L’inventaire contient l’identité des projets, langages, manifests, signaux IaC/CI/container/Kubernetes, indices de services AWS et certaines métadonnées Git. Les dossiers générés, vendor et build sont ignorés.

Le JSON normalisé évite de rescanner en permanence tous les repositories et fournit une interface stable aux agents `architecture-designer`, `platform-architect` et autres spécialistes.

## API locale

```bash
just api
```

Endpoint par défaut :

```text
POST http://127.0.0.1:8765/scan
```

L’API reste limitée à `PROJECTS_ROOT` et n’est pas conçue comme scanner arbitraire du système de fichiers.

## Flux d’architecture typique

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
   `--> contrôles sécurité
```

Les résultats d’architecture doivent distinguer explicitement les faits issus de l’inventaire, les hypothèses et les recommandations.
