# Stratégie des modèles

Le toolkit est provider-agnostic. Les définitions d’agents ne dépendent pas directement de GitHub Copilot, OpenAI, Codex, LiteLLM ou d’un autre provider.

## Trois tiers de capacité

Chaque agent est rattaché à un des trois tiers stables définis dans `profiles/agent-tiers.json` :

| Tier | Modèle Copilot par défaut | Usage typique |
|---|---|---|
| `low` | `github-copilot/gpt-5.6-luna` | tâches bornées, peu risquées et peu coûteuses |
| `medium` | `github-copilot/gpt-5.6-terra` | travail d’ingénierie courant |
| `high` | `github-copilot/gpt-5.6-sol` | architecture, sécurité, arbitrage et raisonnement profond |

Le mapping agent → tier ne dépend pas du provider concret. Par exemple, `docs-writer` reste `low`, `builder` reste `medium` et `platform-architect` reste `high`, même si on passe du profil Copilot à un profil Codex personnel.

## Profils

Les modèles concrets sont définis dans `profiles/*.env.example`.

```bash
just profiles
just profile copilot
just profile codex
just models
```

Le profil de travail par défaut est `copilot`.

Le provider GitHub Copilot d’OpenCode est `github-copilot`. Il faut vérifier les modèles réellement exposés par le compte :

```bash
opencode models github-copilot
```

Si les IDs disponibles diffèrent, il suffit d’éditer `profiles/copilot.env.example` ; aucun agent ni règle de routage n’a besoin d’être modifié.

## Usage personnel / Codex

`profiles/codex.env.example` fournit un profil personnel prêt à être adapté.

```bash
just profile codex
```

On peut utiliser un seul modèle Codex/OpenAI pour les trois tiers, ou attribuer des modèles différents à `MODEL_LOW`, `MODEL_MEDIUM` et `MODEL_HIGH`.

## Overrides par agent

Les overrides persistants doivent être placés dans `.env.local` :

```bash
MODEL_BUILDER=openai/gpt-5.3-codex
MODEL_REVIEWER=github-copilot/gpt-5.6-sol
```

`.env.local` est chargé après `.env` et un changement de profil ne le modifie jamais.

Ordre de résolution :

```text
MODEL_<AGENT> override
        ↓
tier de l’agent dans profiles/agent-tiers.json
        ↓
MODEL_LOW / MODEL_MEDIUM / MODEL_HIGH du profil actif
```

## Pourquoi trois tiers plutôt que 37 modèles fixes ?

Les tiers gardent une politique coût/qualité stable même quand les providers changent. Il suffit de modifier trois valeurs pour migrer les 37 agents sans toucher aux configs OpenCode générées ni au manifest des agents.

`meta-router` garde les tâches normales sur des chemins low/medium et utilise les agents high pour les sujets à risque élevé, faible confiance, sécurité sensible ou architecture complexe.

## LiteLLM

LiteLLM reste optionnel et ne fait pas partie de l’installation par défaut. `just configure` et `just configure-litellm` restent disponibles pour un futur usage gateway. Les credentials utilisés pour la découverte ne sont pas persistés par le configurateur.
