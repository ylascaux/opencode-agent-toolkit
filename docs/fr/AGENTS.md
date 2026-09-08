# Architecture des agents

Le toolkit contient **37 agents**, mais ils ne sont pas tous au même niveau. La hiérarchie est volontaire.

## Plan de contrôle

| Agent | Rôle |
|---|---|
| `meta-router` | classe le travail et choisit un chemin principal |
| `orchestrator` | exécute les livraisons/incidents multi-étapes |
| `review-lead` | sélectionne les dimensions de review indépendantes |
| `security-lead` | sélectionne les gates de sécurité |
| `platform-architect` | dirige le conseil d’architecture |
| `arbiter` | tranche les désaccords matériels |
| `deep-reasoner` | escalade les décisions risquées ou peu certaines |
| `evidence-auditor` | vérifie les affirmations de réussite |

`meta-router` ne voit que les quatre portes d’exécution/lead et les trois agents d’escalade/audit. Il n’a pas un catalogue plat de tous les spécialistes.

## Leaf agents de delivery

`brainstorm`, `planner`, `builder`, `tester`, `mock-generator`, `debugger`, `python-specialist`, `go-specialist`, `terraform-terragrunt`, `cicd`.

## Leaf agents de review

`reviewer`, `api-contract`, `performance`, plus les domaines/sécurités choisis par `review-lead`.

## Leaf agents architecture/platform

`project-scanner`, `architecture-designer`, `aws-platform`, `terraform-terragrunt`, `kubernetes`, `cicd`, `sre`, `observability`, `finops`, `database`, `networking`, `threat-model`, `iac-security`.

## Leaf agents sécurité

`threat-model`, `appsec`, `iac-security`, `supply-chain`, `secrets`, `pentest`.

## Invariant des leaf agents

Chaque leaf possède un deny-all explicite sur `task`/`subagent`. Seuls les cinq agents de routage/orchestration ont des exceptions. Un spécialiste ne peut donc pas contourner le plan de contrôle.

## Contrat des prompts

Chaque prompt généré contient Role, Operating method, Non-negotiables, Evidence discipline, Stop conditions et Handoff. Le comportement spécifique à chaque rôle est défini dans `agents/manifest.json`.
