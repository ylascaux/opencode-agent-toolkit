# Compatibilité OpenCode V1 / V2

Le repository génère deux configurations natives à partir d’une seule source de vérité : `scripts/generate-config`.

```text
opencode.jsonc      # OpenCode V1 stable
opencode.v2.jsonc   # OpenCode 2 beta
```

`just install`, `just config`, `just check`, `just doctor` et le launcher les régénèrent automatiquement afin d’éviter toute divergence entre agents et commandes.

## Choix du runtime

`.env` utilise par défaut :

```dotenv
OPENCODE_MAJOR=1
```

Valeurs :

- `1` : utilise `opencode` et la configuration V1 native ;
- `2` : utilise `opencode2` et la configuration V2 native ;
- `auto` : préfère `opencode2` s’il est installé, sinon utilise `opencode`.

Pour forcer un runtime sur une commande : `just v1` ou `just v2`.

## Différences de syntaxe principales

| Concept | V1 | V2 |
|---|---|---|
| Map des agents | `agent` | `agents` |
| Prompt agent | `prompt` | `system` |
| Permissions | `permission` | `permissions` |
| Permission shell | `bash` | `shell` |
| Permission sous-agent | `task` | `subagent` |
| Map des commandes | `command` | `commands` |

Le générateur traduit la même politique logique vers les deux formats.

## Compaction de contexte native en V2

OpenCode V2 fournit maintenant une compaction de contexte native. Le toolkit n’installe donc pas et ne dépend pas de plugins tiers de type DCP/context-compression.

Le `opencode.v2.jsonc` généré active explicitement les valeurs V2 documentées :

```jsonc
{
  "compaction": {
    "auto": true,
    "keep": {
      "tokens": 15000
    },
    "buffer": 20000
  }
}
```

Cela conserve la compaction automatique avant dépassement de contexte ainsi que la récupération unique après une erreur de context overflow, tout en gardant environ 15k tokens récents et une marge de sécurité de 20k tokens. Les valeurs sont volontairement explicites dans la configuration générée afin de garder un comportement déterministe du toolkit entre les installations.

N’ajoute pas de plugin de pruning V1 comme DCP dans la configuration V2 tant qu’il n’annonce pas une compatibilité V2 explicite et qu’il n’apporte pas une fonction réellement absente de la compaction native.

## Délégation imbriquée

La hiérarchie prévue comporte deux niveaux :

```text
meta-router -> orchestrator -> spécialiste
```

La configuration V1 utilise `subagent_depth: 2` ; la configuration V2 utilise le paramètre expérimental correspondant.

## Recommandation

Conserve V1 comme runtime par défaut tant que les comportements V2 dont tu dépends n’ont pas été validés localement. Tu peux activer V2 à la demande sans changer le reste du toolkit.
