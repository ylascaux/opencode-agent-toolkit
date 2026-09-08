# Agents

Le toolkit définit actuellement 35 agents configurables indépendamment.

## Plan de contrôle

- `meta-router` : classe les tâches, choisit le chemin le moins coûteux suffisant et escalade selon complexité, risque, désaccord ou confiance faible.
- `orchestrator` : exécute les workflows multi-étapes et coordonne les spécialistes.
- `arbiter` : tranche les désaccords matériels à partir des preuves, pas par vote majoritaire.
- `deep-reasoner` : gère les décisions à haut risque, ambiguës, irréversibles ou à faible confiance.
- `evidence-auditor` : vérifie que les conclusions sont soutenues par de vraies preuves.

## Ingénierie générale

- `brainstorm` : explore plusieurs approches réellement différentes.
- `planner` : transforme le besoin en plan exécutable.
- `builder` : implémente des changements production-ready avec scope minimal.
- `reviewer` : review indépendante et en lecture seule.
- `tester` : tests unitaires, intégration et E2E orientés comportement.
- `mock-generator` : mocks, fakes, fixtures et builders.
- `debugger` : recherche de root cause basée sur les preuves.
- `api-contract` : compatibilité API/event/schema et sémantique des erreurs.
- `performance` : latence, concurrence, scalabilité et compromis coût/performance.

## Architecture et plateforme

- `project-scanner` : découverte multi-repositories en lecture seule.
- `architecture-designer` : architecture actuelle/cible, ADR et diagrammes.
- `platform-architect` : pilote les décisions d’architecture multi-domaines.
- `aws-platform` : services AWS, IAM, réseau, fiabilité et coût.
- `terraform-terragrunt` : Terraform/OpenTofu/Terragrunt.
- `kubernetes` : Kubernetes/EKS, scheduling, autoscaling et opérations.
- `cicd` : CI/CD, GitHub Actions, OIDC, artefacts et sécurité de déploiement.
- `sre` : SLO, capacité, modes de panne, DR et risque opérationnel.
- `observability` : logs, métriques, traces, dashboards et alerting.
- `finops` : coûts AWS/plateforme et arbitrages coût/performance.
- `database` : PostgreSQL/Aurora, schéma, requêtes, migrations, HA et sauvegardes.
- `networking` : VPC, DNS, CloudFront/WAF, TLS, ingress et accès privés.

## Langages

- `python-specialist` : services Python typés, automatisation et tests.
- `go-specialist` : services Go, CLI, concurrence et intégrations AWS.

## Sécurité

- `threat-model` : actifs, acteurs, trust boundaries, abuse cases et mitigations.
- `appsec` : sécurité applicative et logique métier.
- `iac-security` : sécurité Terraform/Kubernetes/AWS.
- `supply-chain` : dépendances, CI, images et provenance.
- `secrets` : détection de credentials/données sensibles avec sortie masquée.
- `pentest` : validation runtime explicitement autorisée, limitée et non destructive.

## Documentation

- `docs-writer` : README, ADR, runbooks et guides de migration basés sur l’implémentation vérifiée.

## Règles d’indépendance

Un agent d’implémentation ne doit pas être le seul reviewer de son propre travail. Les problèmes sécurité sont examinés par des agents dédiés. Les désaccords matériels vont vers `arbiter`, les décisions risquées ou peu sûres vers `deep-reasoner`, et les affirmations de complétion importantes peuvent être vérifiées par `evidence-auditor`.
