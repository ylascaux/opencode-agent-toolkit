# Fiabilité des agents et garde-fous de coût

Le toolkit combine des garde-fous déterministes et des règles de supervision dans les leads. Le principe reste simple : **les LLM décident du travail d'ingénierie ; le runtime décide des limites de sécurité opérationnelle**.

## Profils de fiabilité

`reliability.json` définit trois profils :

| Profil | Parallèle | Queue | Stall | Durée enfant | Retries | Coût enfant* | Coût run* |
|---|---:|---:|---:|---:|---:|---:|---:|
| `cheap` | 2 | 300s | 120s | 600s | 1 | 0.25 | 1.00 |
| `normal` | 3 | 600s | 180s | 900s | 2 | 0.50 | 2.00 |
| `premium` | 4 | 900s | 240s | 1200s | 2 | 1.50 | 5.00 |

`normal` est le profil par défaut. Les valeurs de coût marquées `*` utilisent **la valeur remontée par OpenCode/provider**, dans son unité native. Le toolkit ne convertit pas arbitrairement en EUR.

```bash
RELIABILITY_PROFILE=normal
```

Toute valeur explicite dans `.env.local` prend le dessus sur le profil.

## Parallélisme global et par lead

Le plafond global reste :

```bash
MAX_PARALLEL_SUBAGENTS=3
```

On peut maintenant affiner par lead :

```bash
MAX_PARALLEL_META_ROUTER=2
MAX_PARALLEL_ORCHESTRATOR=3
MAX_PARALLEL_REVIEW_LEAD=3
MAX_PARALLEL_PLATFORM_ARCHITECT=3
MAX_PARALLEL_SECURITY_LEAD=2
```

Si une limite spécifique n'est pas définie, la valeur globale est utilisée.

Le runtime suit les vraies child sessions et les réservations de lancement. Une réservation est consommée dès que le child correspondant apparaît via les événements ou `session.children()`. Cela évite à la fois :

- de dépasser la limite lors d'un burst concurrent ;
- de compter temporairement un même lancement deux fois (`pending + child actif`).

Quand tous les slots sont occupés, la délégation attend dans une queue **sans appel LLM supplémentaire**. `SUBAGENT_QUEUE_TIMEOUT_SECONDS` borne cette attente.

## Preflight avant le premier token coûteux

`oc` / `just run` exécute le preflight avant OpenCode :

- binaire sélectionné présent ;
- config JSON valide ;
- watchdog V1/V2 présent et branché ;
- profil reliability valide ;
- paramètres numériques valides ;
- modèles réellement configurés dans les agents disponibles via `opencode models` ;
- auth disponible pour les providers connus nécessitant une authentification OpenCode ;
- état Git observable.

Contrôles configurables :

```bash
OPENCODE_PREFLIGHT=1
OPENCODE_PREFLIGHT_AUTH=1
OPENCODE_PREFLIGHT_MODELS=1
# OPENCODE_PREFLIGHT_STRICT=1
```

Le script reste compatible avec le Bash 3 fourni par défaut sur macOS.

## Watchdog V1 et V2

V1 et V2 gardent les mêmes capacités fonctionnelles :

- suivi individuel des sessions enfants ;
- distinction `lastActivityAt` / `lastProgressAt` ;
- `WAITING_PERMISSION` exclu du stall ;
- durée maximale ;
- détection de stall tenant compte de l'activité ;
- erreurs répétées ;
- queue et plafond de parallélisme ;
- réconciliation `session.children()` quand disponible ;
- checkpoints de métadonnées ;
- budgets de coût lorsque le provider fournit la donnée.

V2 conserve en plus le hook de retry provider :

```text
400 / 401 / 403 / 404 -> terminal
429                  -> retry borné
5xx                  -> retry borné
```

## Détection de stall tenant compte de l'activité

Un child n'est plus considéré comme bloqué uniquement parce qu'il n'a pas produit récemment de modification de fichier, de diff, de todo ou d'autre événement qualifié de progrès matériel. Le watchdog exige maintenant simultanément :

1. aucun progrès matériel depuis plus de `SUBAGENT_STALLED_TIMEOUT_SECONDS` ;
2. aucun heartbeat runtime/message depuis plus de `SUBAGENT_HEARTBEAT_TIMEOUT_SECONDS` ;
3. aucun appel de tool encore en cours ;
4. la même situation toujours présente au cycle de watchdog suivant.

Valeurs par défaut du profil `normal` :

```bash
SUBAGENT_HEARTBEAT_TIMEOUT_SECONDS=60
SUBAGENT_STALLED_TIMEOUT_SECONDS=180
SUBAGENT_WATCH_INTERVAL_SECONDS=15
```

Cela protège les longues phases de réflexion, lecture, analyse ou génération de message contre les annulations à tort, tout en conservant une récupération déterministe des vrais stalls.

Lorsqu'un child doit malgré tout être interrompu pour une raison retryable, le watchdog persiste d'abord la délégation existante et son `task_id` avec le statut `retryable_failed`, **avant** d'envoyer l'interruption. Une nouvelle tentative de la même délégation reprend donc la task connue au lieu de recréer silencieusement un child vide et de perdre le contexte déjà produit.

## Détection de boucle outil

Le watchdog mémorise la signature de l'appel et de son résultat. Si un child exécute plusieurs fois **le même tool avec les mêmes arguments et obtient le même résultat**, cette activité n'est plus considérée comme un progrès.

Au-delà de `MAX_SAME_ERROR`, le child peut être interrompu.

Cela couvre des boucles du type :

```text
commande A -> résultat X
commande A -> résultat X
commande A -> résultat X
```

que le simple compteur de steps ne diagnostique pas correctement.

## Budgets de coût remontés par le provider

```bash
MAX_CHILD_COST=0.50
MAX_RUN_COST=2.00
```

`0` désactive la limite monétaire correspondante.

Le garde-fou n'est actif que lorsque OpenCode/provider remonte un champ de coût exploitable. S'il n'y a aucune télémétrie de coût, **aucun coût n'est inventé** : steps, durée, stall, retries, profondeur et parallélisme restent les barrières sûres.

`MAX_CHILD_COST` coupe un child dépassant son budget remonté. `MAX_RUN_COST` coupe la famille de sessions du run lorsque le total remonté dépasse la limite.

## Checkpoints

Le watchdog persiste uniquement des **métadonnées**, jamais le prompt ni une copie du code :

```text
${XDG_STATE_HOME:-$HOME/.local/state}/opencode-agent-toolkit/runs/<session-id>.json
```

Surcharge possible :

```bash
RELIABILITY_STATE_DIR=$HOME/.local/state/opencode-agent-toolkit/runs
```

Un checkpoint contient notamment :

- session ID et parent ;
- agent ;
- statut ;
- raison d'abort ;
- état de retry de la délégation si applicable ;
- coût remonté ;
- timestamps de démarrage, activité et progrès.

La session OpenCode et les handoffs restent la source de vérité pour le contenu détaillé du travail.

## Caps de steps

Les overrides de steps sont des **plafonds**, pas des valeurs absolues permettant d'augmenter la liberté d'un agent.

```bash
MAX_STEPS_BUILDER=7    # peut réduire
MAX_STEPS_BUILDER=999  # ne peut pas dépasser la limite du générateur
```

`scripts/apply-reliability` applique :

```text
steps effectifs = min(steps générés, cap reliability)
```

## Politique d'arrêt

Comportement attendu :

- auth/config/provider/modèle non retryable -> arrêt rapide ;
- `429` / `5xx` -> retry borné ;
- même erreur racine sans nouvelle preuve -> arrêt ;
- même tool + mêmes args + même résultat -> boucle détectable ;
- absence de progrès **et** de heartbeat, confirmée au cycle suivant -> interruption ;
- activité ou tool encore en cours -> pas considéré comme stall ;
- child trop long -> interruption ;
- child au-dessus du coût remonté -> interruption si télémétrie disponible ;
- `WAITING_PERMISSION` -> pas considéré comme stall ;
- limite parallèle atteinte -> attente dans la queue ;
- abort watchdog retryable -> conservation et réutilisation du `task_id` connu ;
- child bloqué/aborté -> consommer handoff/checkpoint avant de décider d'un remplacement.

## Commandes utiles

```bash
just reliability
just preflight
just doctor
just check
```

`just reliability` affiche la politique effective après profil et overrides locaux.
