# Fiabilité des agents

Le toolkit combine des garde-fous déterministes et des règles de supervision dans les leads. Le principe devient : **les LLM décident du travail d'ingénierie ; le runtime applique les limites sûres, mais un signal watchdog ambigu ne doit jamais détruire du travail automatiquement**.

## Profils de fiabilité

`reliability.json` définit trois profils :

| Profil | Parallèle | Queue | Heartbeat | Stall | Durée enfant | Retries délégation |
|---|---:|---:|---:|---:|---:|---:|
| `cheap` | 2 | 300s | 45s | 120s | 600s | 1 |
| `normal` | 3 | 600s | 60s | 180s | 900s | 2 |
| `premium` | 4 | 900s | 90s | 240s | 1200s | 2 |

`normal` reste le profil par défaut. Les valeurs explicites dans `.env.local` prennent le dessus sur le profil.

Les budgets monétaires remontés par le provider ne font volontairement **plus partie** du runtime. `MAX_CHILD_COST` et `MAX_RUN_COST` sont supprimés : la télémétrie de coût n'est pas assez fiable pour justifier l'interruption destructive d'une session.

## Parallélisme global et par lead

Le plafond global reste :

```bash
MAX_PARALLEL_SUBAGENTS=3
```

Overrides facultatifs :

```bash
MAX_PARALLEL_META_ROUTER=2
MAX_PARALLEL_ORCHESTRATOR=3
MAX_PARALLEL_REVIEW_LEAD=3
MAX_PARALLEL_PLATFORM_ARCHITECT=3
MAX_PARALLEL_SECURITY_LEAD=2
```

Le runtime suit les child sessions actives et les réservations de lancement afin d'éviter de dépasser la limite lors de délégations concurrentes. Quand tous les slots sont occupés, la délégation attend dans une queue déterministe sans nouvel appel LLM.

## Watchdog avec approbation utilisateur

La télémétrie OpenCode peut être incomplète alors qu'un agent est toujours en train de réfléchir ou d'attendre dans le runtime. Donc **le silence est un soupçon, pas la preuve d'un stall**.

Les wrappers V1/V2 actifs neutralisent les interruptions automatiques basées sur les heuristiques suivantes :

- absence de progrès observable ;
- durée maximale du child ;
- répétitions détectées par heuristique ;
- coût provider child/run.

Les anciens watchdogs restent isolés pour compatibilité et tests de régression, mais ces heuristiques destructives ne sont plus autorisées pendant un run normal.

### OpenCode V2

V2 charge `./plugins/reliability-approval` en plus du plugin runtime. Ce plugin observe l'activité indépendamment et émet un événement `suspected` lorsqu'un child semble bloqué ou dépasse sa durée configurée.

Le TUI demande ensuite explicitement à l'utilisateur avant toute action destructive. `session.interrupt()` n'est appelé **que si l'utilisateur choisit Kill**.

Si la session redevient active avant que la décision n'arrive au serveur, la demande est considérée comme obsolète et aucune interruption n'est effectuée. Si le TUI est absent, déconnecté ou si l'événement d'approbation ne peut pas être transmis, le système **fail open** et ne tue pas la session.

Le choix **Keep running** remet à zéro la fenêtre d'observation et évite de reproposer immédiatement le même popup.

### OpenCode V1 / mode headless

V1 ne fournit pas actuellement une surface de confirmation suffisamment fiable pour ce workflow. Les heuristiques watchdog passent donc en **fail open** : la session est conservée au lieu d'être tuée automatiquement.

## Ce qui peut encore arrêter une session

Ce changement concerne les heuristiques ambiguës du watchdog. OpenCode peut toujours terminer lui-même une session sur une erreur runtime/provider terminale. Le runtime legacy distingue aussi les erreurs explicites non retryable de configuration/provider. Ces décisions ne sont pas déduites d'un simple silence.

## Retry et identité de la task

L'état de retry conserve toujours le `task_id` connu lorsqu'une terminaison retryable est réellement observée. Une nouvelle tentative de la même délégation doit reprendre le child connu plutôt que recréer silencieusement un leaf vide.

Les siblings déjà terminés et le lead parent ne doivent pas être redémarrés uniquement parce qu'un leaf échoue.

## Permission et supervision

`WAITING_PERMISSION` n'est jamais un stall. Un lead ayant un child actif est `WAITING_ON_CHILD`, même si le lead lui-même reste silencieux.

Les prompts des leads indiquent explicitement qu'un silence watchdog doit être traité comme `STALL_SUSPECTED` uniquement, sans remplacement ni annulation avant décision utilisateur.

## Checkpoints

Les métadonnées sont stockées sous :

```text
${XDG_STATE_HOME:-$HOME/.local/state}/opencode-agent-toolkit/runs/<session-id>.json
```

Surcharge facultative :

```bash
RELIABILITY_STATE_DIR=$HOME/.local/state/opencode-agent-toolkit/runs
```

Les checkpoints contiennent les métadonnées de session/délégation, statuts, timestamps et raisons d'abort. Ils ne copient volontairement ni les prompts ni le code du projet.

## Caps de steps

Les overrides restent des plafonds :

```bash
MAX_STEPS_BUILDER=7    # peut réduire
MAX_STEPS_BUILDER=999  # ne peut pas dépasser la limite policy/générateur
```

`scripts/apply-reliability` applique :

```text
steps effectifs = min(steps générés, cap reliability)
```

## Politique attendue

- absence de heartbeat/progrès -> suspicion uniquement, jamais kill automatique ;
- durée maximale -> suspicion uniquement, jamais kill automatique ;
- child suspect en V2 -> demander à l'utilisateur avant interruption ;
- child suspect en V1/headless -> fail open ;
- `WAITING_PERMISSION` -> pas un stall ;
- tool actif/en cours -> pas un stall ;
- limite parallèle atteinte -> attente dans la queue runtime ;
- kill explicitement approuvé -> interruption de ce child uniquement ;
- terminaison retryable -> conservation/réutilisation du `task_id` connu si possible ;
- télémétrie monétaire provider -> jamais utilisée comme limite de kill.

## Commandes utiles

```bash
just reliability
just preflight
just doctor
just check
```

`just reliability` affiche les limites effectives et le mode d'approbation actif.
