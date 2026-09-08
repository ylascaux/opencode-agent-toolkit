# Routage et stratégie de modèles

## Routage minimal suffisant

Le routeur cherche le chemin le moins coûteux qui reste suffisamment fiable. Le risque, l’incertitude et le blast radius passent avant l’optimisation de coût.

| Situation | Routage |
|---|---|
| Faible complexité + faible risque | Un spécialiste ciblé |
| Changement comportemental moyen | Spécialiste + tester + reviewer |
| Multi-domaines / migration / gros blast radius | Orchestrator + spécialistes pertinents |
| Nouvelle trust boundary | Ajouter threat-model et contrôles sécurité utiles |
| Désaccord matériel | Ajouter arbiter |
| Risque élevé / confiance faible / choix irréversible | Ajouter deep-reasoner |
| Complétion non triviale | Ajouter evidence-auditor |

Les analyses indépendantes en lecture seule peuvent être parallélisées si le runtime le permet. Les tâches ayant une vraie dépendance doivent rester séquentielles.

## Confiance

Les décisions finales exposent un niveau de confiance :

- `high` : les preuves directes soutiennent la conclusion et les contrôles pertinents passent ;
- `medium` : conclusion probablement correcte mais certaines preuves restent indirectes ou des hypothèses subsistent ;
- `low` : incertitude importante, preuves manquantes ou désaccord non résolu.

Une confiance faible sur un changement à fort impact doit déclencher une escalade.

## Niveaux de modèles

Stratégie pratique :

- **rapide/économique** : scan, mocks, docs, classification simple et transformations répétitives ;
- **fort en code** : builder, Python, Go, Terraform, CI/CD, Kubernetes ;
- **fort en raisonnement** : orchestrator, architecture, reviewer, threat-model, AppSec ;
- **raisonnement profond** : `deep-reasoner`, arbitrage difficile, migration majeure ou architecture critique.

Chaque agent mappe une variable `MODEL_*`, ce qui laisse LiteLLM effectuer le routage concret.

## Familles de modèles indépendantes

Si possible, évite d’utiliser la même famille de modèle pour l’implémentation et l’approbation indépendante. Un modèle spécialisé code peut construire, puis une autre famille orientée raisonnement/sécurité peut reviewer.

## Smart Router

Le `.env.example` utilise `litellm/smart-router` partout par défaut. Tu peux ensuite figer uniquement les rôles critiques sur des groupes de modèles précis et conserver Smart Router pour les tâches courantes.
