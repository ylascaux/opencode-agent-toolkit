# Stratégie des modèles

Chaque agent conserve sa propre variable `MODEL_*`, mais le choix des modèles doit être piloté par des profils de capacité plutôt que par 37 choix indépendants difficiles à maintenir.

## Profils

| Profil | Rôles typiques | Objectif |
|---|---|---|
| `fast` | brainstorm, scanner, mocks, secrets, docs | faible latence/coût pour les tâches bornées |
| `general` | meta-router, planner, observability, FinOps | bon raisonnement général |
| `coding` | builder, tester, Python, Go, Terraform, CI/CD | implémentation et tool use fiables |
| `reasoning` | orchestrator, debugger, AWS, Kubernetes, database, networking, threat-model | décisions techniques plus difficiles |
| `deep` | platform-architect, deep-reasoner | décisions complexes ou difficiles à inverser |
| `review` | review-lead, reviewer, evidence-auditor, API contract, supply-chain | review critique indépendante |
| `security` | security-lead, AppSec, IaC security, pentest | analyse et validation sécurité |

`just configure` découvre `/v1/models`, propose des modèles par profil, puis applique les profils retenus aux 37 agents.

## Indépendance

Quand c’est possible, utiliser une famille de modèles différente entre implémentation et review/sécurité indépendante permet de réduire les angles morts corrélés. Il ne faut toutefois pas forcer cette diversité si le modèle alternatif est nettement moins adapté.

## Coût des escalades

Les modèles deep/raisonnement coûteux ne doivent pas être utilisés systématiquement. Les tâches bornées et peu risquées restent sur `fast`/`general`/`coding`. Risque élevé, décision difficile à inverser, désaccord matériel ou faible confiance justifient l’escalade vers `reasoning`/`deep`.

## Credentials du gateway

`just configure` peut lire `LITELLM_API_KEY`, `CF_ACCESS_TOKEN` et `LITELLM_HEADERS_JSON` depuis l’environnement du processus. Seuls les mappings de modèles sont écrits ; les credentials ne sont pas persistés par le configurateur.
