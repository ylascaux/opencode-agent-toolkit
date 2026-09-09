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

Les budgets monétaires remontés par le provider ne font volontairement **plus partie** du runtime. `MAX_CHILD_COST` et `MAX_RUN_COST` sont supprimés : la télémétrie de coût n'est pas assez fiable pour justifier l'interruption destructive d'une session. Les anciennes valeurs encore présentes dans un `.env` local sont ignorées par les wrappers actifs.

## Gate de validation du plan

`reliability.json` définit aussi `plan_approval.default_mode`, avec `changes` par défaut. Le mode effectif peut être surchargé via `PLAN_APPROVAL_MODE` :

```bash
PLAN_APPROVAL_MODE=changes   # défaut : découverte puis validation avant mutation
# PLAN_APPROVAL_MODE=off     # pas de gate de plan
# PLAN_APPROVAL_MODE=always  # gate aussi la délégation au-delà de la découverte directe
```

Le gate est imposé par le runtime OpenCode V2. Il suit la session racine et les relations parent/enfant afin qu'une validation donnée par l'utilisateur racine s'applique aux leaf agents de la demande approuvée, sans se propager aux demandes suivantes. En V1, le plugin et les pauses d'approbation sont désactivés.

Avant validation, les opérations de lecture, recherche et découverte restent disponibles. En mode `changes`, le runtime bloque les outils mutateurs, les commandes shell mutatrices ou inconnues et la délégation orientée implémentation. Les agents de planification en lecture seule restent disponibles afin de produire un plan fondé sur des preuves sans créer de deadlock.

Un plan en attente se termine par `PLAN_APPROVAL_REQUIRED`. Les réponses courtes explicites comme `go`, `approve`, `oui` ou `valide` n'approuvent qu'un plan actuellement en attente. Les mots de rejet maintiennent le blocage. Toute autre réponse de l'utilisateur racine est considérée comme un changement de périmètre et réinitialise le plan.

Si l'agent détecte après validation un changement matériel de périmètre, de dépendance, de trust boundary, d'étape destructive, de rollback ou de validation, il doit s'arrêter avant toute nouvelle mutation et émettre `PLAN_REAPPROVAL_REQUIRED`. Le runtime révoque alors l'autorisation courante jusqu'à validation explicite du plan révisé.

Le garde-fou runtime est autoritaire : un modèle ne peut pas contourner une validation manquante simplement en sautant le prompt de planification. Un outil mutateur bloqué fait passer l'état en attente de plan et l'agent doit présenter le plan au lieu de réessayer.

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

Les wrappers V1/V2 actifs neutralisent les interruptions automatiques basées sur l'absence de progrès observable, la durée maximale du child, les répétitions détectées par heuristique et le coût provider. Les anciens watchdogs restent isolés sous la forme `*-legacy` afin de conserver et tester la queue, les retries de délégation et l'identité des tasks.

### OpenCode V2

V2 charge `./plugins/reliability-approval` en plus du plugin runtime. Ce plugin observe l'activité indépendamment et émet un événement `suspected` lorsqu'un child semble bloqué ou dépasse sa durée configurée.

Le TUI demande ensuite explicitement à l'utilisateur avant toute action destructive. `session.interrupt()` n'est appelé **que si l'utilisateur choisit Kill**.

Si la session redevient active avant que la décision n'arrive au serveur, la demande est considérée comme obsolète et aucune interruption n'est effectuée. Si le TUI est absent, déconnecté ou si l'événement d'approbation ne peut pas être transmis, le système **fail open** et ne tue pas la session.

Le choix **Keep running** remet à zéro la fenêtre d'observation et évite de reproposer immédiatement le même popup.

### OpenCode V1 / mode headless

V1 ne fournit pas actuellement une surface de confirmation suffisamment fiable pour ce workflow. Les heuristiques watchdog passent donc en **fail open** : la session est conservée au lieu d'être tuée automatiquement.

## Retry et identité de la task

L'état de retry conserve toujours le `task_id` connu lorsqu'une terminaison retryable est réellement observée. Une nouvelle tentative de la même délégation doit reprendre le child connu plutôt que recréer silencieusement un leaf vide.

Les siblings déjà terminés et le lead parent ne doivent pas être redémarrés uniquement parce qu'un leaf échoue.

## Permission et supervision

`WAITING_PERMISSION` n'est jamais un stall. Un lead ayant un child actif est `WAITING_ON_CHILD`, même si le lead lui-même reste silencieux.

Les prompts générés des leads indiquent explicitement qu'un silence watchdog doit être traité comme `STALL_SUSPECTED` uniquement, sans remplacement ni annulation avant décision utilisateur.

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

- mutation non approuvée -> stop et demande de validation du plan ;
- déviation matérielle du périmètre approuvé -> stop et demande de revalidation ;
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

`just reliability` affiche les limites effectives et le mode de validation du plan actif.
