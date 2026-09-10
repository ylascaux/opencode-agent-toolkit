# Architecture des agents

Le toolkit contient actuellement **40 agents**. Chaque agent est désormais un composant autonome sous `agents/<nom>/`.

Pour le format complet, voir [CONFIGURATION_AGENTS.md](./CONFIGURATION_AGENTS.md).

## Organisation

```text
agents/<nom>/
├── agent.json
├── prompt.md
└── permissions.json
```

Le socle partagé vit sous :

```text
agents/_defaults/
├── agent.json
├── prompt.md
└── permissions.json
```

Les artefacts runtime sont générés ; il ne faut pas éditer `.generated/`, `opencode.jsonc` ou `opencode.v2.jsonc` comme sources.

## Plan de contrôle

| Agent | Rôle |
|---|---|
| `meta-router` | classe le travail et choisit un chemin principal |
| `orchestrator` | exécute les livraisons/incidents multi-étapes et les workflows de recherche externe structurée |
| `review-lead` | sélectionne les dimensions de review indépendantes |
| `security-lead` | sélectionne les gates de sécurité |
| `platform-architect` | dirige le conseil d’architecture |
| `arbiter` | tranche les désaccords matériels |
| `deep-reasoner` | escalade les décisions risquées ou peu certaines |
| `evidence-auditor` | vérifie les affirmations de réussite |

La hiérarchie reste volontairement courte :

```text
meta-router
  -> lead/orchestrator
      -> leaf specialist
```

La profondeur maximale reste 2.

La topologie est déclarée par l'enfant via `agent.json.parents`. Ajouter un agent à un ou plusieurs leads ne demande donc plus de modifier une map centrale.

Les leaf agents génériques de recherche structurée sont :

- `source-discovery` : découverte LOW de sources candidates ; il ne certifie jamais des faits métier ;
- `structured-extractor` : extraction structurée MEDIUM à partir des preuves fournies et d’un schéma appartenant à l’appelant ;
- `entity-resolver` : résolution d’identité MEDIUM sans modifier les données canoniques.

Voir [RESEARCH_PIPELINE.md](./RESEARCH_PIPELINE.md) pour la frontière d’orchestration externe et la politique d’escalade.

## Permissions

Les leaf agents gardent un deny-all déterministe sur `task`/`subagent`. Les exceptions de délégation sont dérivées automatiquement des `parents` déclarés dans les agents enfants.

Les permissions opérationnelles héritent de `agents/_defaults/permissions.json` et peuvent être surchargées dans `agents/<nom>/permissions.json`.

## Ajouter un agent

```bash
just new-agent cloudflare --parent platform-architect --tier medium --model-profile reasoning
```

Puis modifier le répertoire créé et valider :

```bash
just config
just check
```

`just agents` affiche le catalogue découvert, les modèles, parents et enfants.
