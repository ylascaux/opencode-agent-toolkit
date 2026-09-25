# V2 — État d'implémentation

## Résumé

Les deux fondations prévues pour la V2 sont maintenant implémentées :

| Axe | État |
| --- | --- |
| mémoire locale `harness-memory` | implémenté |
| mémoire PostgreSQL partagée | implémenté |
| identité projet stable | implémenté |
| contexte borné + MCP mémoire | implémenté |
| capture automatique directe | implémenté |
| ACP v1 OpenCode | implémenté |
| permissions ACP explicites | implémenté |
| pool ACP parallèle borné | implémenté |
| isolation child/parent | implémenté |
| V1 → V2 migration | volontairement non implémentée |

## Mémoire

Flux quotidien :

```text
OpenCode session
  → extraction automatique
  → toolkit bridge
  → harness-memory
       ├── local SQLite
       └── PostgreSQL partagé
```

Le backend V2 par défaut est `local`. Le backend `postgres` utilise le même namespace sur deux clones ayant le même remote Git.

La CI qualifie :

- le vrai package `harness-memory` en SQLite ;
- deux clients sur un vrai PostgreSQL ;
- lecture croisée ;
- écritures concurrentes distinctes.

Le backend `legacy` reste uniquement pour compatibilité explicite.

## ACP

Flux :

```text
parent
  → oat-acp MCP
  → bounded pool
  → ACP child process
  → initialize
  → session/new
  → session/prompt
  → session/update
  → permission / respond
  → close
```

`start`, `message` et `respond` sont asynchrones du point de vue MCP ; le parent poll `status`.

Les sessions et jobs restent volontairement éphémères. Aucun broker/daemon n'est ajouté.

## Sécurité

- runners sur liste approuvée ;
- `trusted=false` interdit l'exécution ;
- child cwd limité au workspace parent ;
- aucun `oat-acp` récursif chez le child ;
- aucun `oat-memory` chez le child ;
- DSN PostgreSQL retiré de l'environnement child ;
- capture mémoire child désactivée ;
- DSN non sérialisé dans `OPENCODE_CONFIG_CONTENT`.

## Exploitation

Validation locale :

```bash
just install
just doctor
oc memory status
oc runner doctor
```

Partage PostgreSQL :

```bash
oc memory configure-postgres 'postgresql://USER:PASSWORD@HOST:5432/DB'
```

Retour local :

```bash
oc memory configure-local
```

## Reste optionnel, non bloquant

Ces sujets ne sont pas nécessaires au runtime V2 actuel :

- persistance des jobs ACP après crash ;
- UI dédiée ;
- partage des checkpoints/conversations entre machines ;
- backend de queue externe ;
- export Markdown périodique de la mémoire V2 ;
- orchestration de runners ACP autres qu'OpenCode.

Ils ne doivent être ajoutés qu'en réponse à un besoin réel.
