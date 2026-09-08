# Architecture

Le toolkit sépare volontairement les responsabilités en plusieurs plans.

## 1. Plan de contrôle

`meta-router` est le point d’entrée par défaut. Il classe la demande et choisit le chemin minimal suffisant sans implémenter directement.

`orchestrator` gère les workflows multi-étapes et coordonne implémentation, tests, review et contrôles sécurité/opérationnels.

`arbiter` tranche les désaccords matériels à partir des preuves. `deep-reasoner` gère les décisions à haut risque, ambiguës, coûteuses ou à faible confiance. `evidence-auditor` vérifie que les affirmations de réussite sont réellement soutenues par des preuves reproductibles.

## 2. Plan d’ingénierie

Boucle générale :

```text
brainstorm -> planner -> builder/spécialiste -> tester -> reviewer
```

Les spécialistes couvrent notamment Python, Go, Terraform/Terragrunt, CI/CD, contrats API, performance, base de données et réseau.

## 3. Conseil d’architecture Platform

```text
project-scanner
      |
      v
platform-architect
  |-- architecture-designer
  |-- aws-platform
  |-- kubernetes
  |-- terraform-terragrunt
  |-- networking
  |-- database
  |-- sre
  |-- observability
  |-- finops
  |-- threat-model
  `-- iac-security
```

Le conseil doit distinguer les faits observés, les hypothèses et les recommandations. Les décisions importantes doivent couvrir les modes de panne, la migration/rollback, la sécurité, la charge opérationnelle et les facteurs de coût.

## 4. Plan sécurité

La sécurité est indépendante du builder :

```text
threat-model
appsec
iac-security
supply-chain
secrets
pentest
```

Le routeur ne sélectionne que les contrôles pertinents selon la surface d’attaque modifiée.

## 5. Plan de preuves

Les preuves peuvent inclure :

- diff et fichiers modifiés ;
- commandes de tests exactes et résultats ;
- validation/plan Terraform ou OpenTofu ;
- logs, métriques et traces ;
- validation HTTP/runtime sûre ;
- inventaire JSON des sources ;
- hypothèses explicites et questions ouvertes.

`evidence-auditor` classe les affirmations en vérifiées, partiellement vérifiées, non vérifiées ou contredites.

## 6. Découverte multi-repositories

`project-scanner` lit `PROJECTS_ROOT` (par défaut `$HOME/Projects`) sans modifier les projets. Le scanner Python normalise les métadonnées dans `architecture-inventory.json`, ensuite consommé par les agents d’architecture.

## 7. Indépendance des modèles

Chaque agent possède sa variable de modèle. Tu peux donc utiliser un modèle peu coûteux pour le scan, un bon modèle de code pour l’implémentation, une autre famille pour la review et un modèle de raisonnement profond uniquement en cas d’escalade.
