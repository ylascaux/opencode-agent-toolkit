# Configuration des agents

Chaque agent est un composant autonome sous `agents/<nom>/`.

```text
agents/
├── _defaults/
│   ├── agent.json
│   ├── prompt.md
│   └── permissions.json
├── meta-router/
│   ├── agent.json
│   ├── prompt.md
│   └── permissions.json
└── ...
```

## Source de vérité

La source de vérité éditable est le répertoire de l'agent. Il n'y a plus de manifest central éditable, de catalogue central de permissions, ni de fichier central de tiers de modèles.

- `agent.json` : description, mode OpenCode, variable de modèle, tier de qualité, profil LiteLLM optionnel, budget de steps, parents et options OpenCode spécifiques.
- `prompt.md` : comportement spécifique à l'agent.
- `permissions.json` : uniquement les overrides de permissions propres à l'agent.
- `agents/_defaults/*` : valeurs communes héritées par tous les agents.

`just config` découvre automatiquement les répertoires, valide le graphe, fusionne les defaults et génère `.generated/`, `opencode.jsonc` et `opencode.v2.jsonc`.

## Exemple

```json
{
  "description": "Use for Cloudflare architecture and migration analysis.",
  "mode": "subagent",
  "model_env": "MODEL_CLOUDFLARE",
  "tier": "medium",
  "model_profile": "reasoning",
  "steps": 16,
  "parents": ["platform-architect"],
  "opencode": {}
}
```

`parents` est déclaré par l'enfant. Ajouter un agent ne demande donc pas de modifier une map `LEAD_CHILDREN` centrale ni le fichier de son parent.

## Composition du prompt

Le prompt runtime final est composé de :

1. `# Role` généré depuis `agent.json.description`
2. `agents/<nom>/prompt.md`
3. `agents/_defaults/prompt.md`
4. la supervision de fiabilité déterministe ajoutée aux agents capables de déléguer

Les prompts générés vivent dans `.generated/prompts/` et ne doivent pas être édités directement.

## Permissions

`agents/_defaults/permissions.json` est le socle commun. `agents/<nom>/permissions.json` le surcharge récursivement.

Politique par défaut :

- `websearch` : allow
- `webfetch` : allow
- lectures shell/repo sûres : allow
- opérations shell inconnues non destructives : ask
- lectures sensibles : ask
- édition : ask sauf override explicite
- opérations clairement destructives : deny

La délégation (`task` / `subagent`) est dérivée de `parents` et n'est pas configurable dans `permissions.json`, afin d'éviter toute divergence entre topologie et permissions.

## Modèles

`tier` vaut `low`, `medium` ou `high` et utilise `MODEL_LOW`, `MODEL_MEDIUM` ou `MODEL_HIGH`.

`model_env` permet un override par agent, par exemple `MODEL_CLOUDFLARE`.

`model_profile` n'est qu'un indice pour la découverte LiteLLM optionnelle. LiteLLM n'est pas requis.

`just config` ne contacte jamais LiteLLM et ne demande aucune configuration de provider. La découverte LiteLLM est explicite :

```bash
just configure-litellm
```

## Ajouter un agent

```bash
just new-agent cloudflare --parent platform-architect --tier medium --model-profile reasoning
```

Puis éditer :

```text
agents/cloudflare/agent.json
agents/cloudflare/prompt.md
agents/cloudflare/permissions.json
```

et valider :

```bash
just config
just check
```

## Validation

La génération échoue avant OpenCode si elle détecte : JSON invalide, fichier manquant, parent inconnu, cycle, chemin de délégation supérieur à deux niveaux, variable de modèle dupliquée, tier/profil invalide, effet de permission invalide ou tentative de définir la topologie dans `permissions.json`.
