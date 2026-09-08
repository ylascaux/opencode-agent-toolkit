# Fiabilité du runtime

Le toolkit combine deux couches complémentaires : des garde-fous déterministes dans le runtime et des règles de supervision dans les agents leads. L’objectif est d’échouer tôt, de borner le coût et de conserver le travail déjà terminé au lieu de découvrir un problème d’authentification, de provider ou de sous-agent bloqué après une longue exécution.

## Preflight

Le launcher exécute `scripts/preflight` avant que OpenCode ne démarre la première session modèle. Il vérifie le binaire sélectionné, les modèles résolus, les paramètres runtime, l’installation du watchdog, l’authentification pour les providers connus, la disponibilité des modèles côté provider et l’état Git de base du workspace.

Une erreur bloquante arrête tout avant le premier appel modèle :

```text
Preflight failed with 1 blocking issue(s). No agent session was started.
```

Ne désactive un contrôle que si tu acceptes volontairement le risque :

```bash
OC_PREFLIGHT=0
OC_PREFLIGHT_AUTH=0
OC_PREFLIGHT_MODELS=0
```

## Limites de steps conservatrices

`generate-config` reste responsable du catalogue d’agents et des permissions. `apply-runtime-policy` applique ensuite une passe déterministe avec des plafonds de steps plus conservateurs et injecte les règles de supervision des sous-agents dans les cinq leads.

Par défaut, aucun agent ne dépasse 16 steps. Il est possible de surcharger globalement ou par agent dans `.env.local` :

```bash
OC_DEFAULT_AGENT_STEPS=12
OC_STEPS_ORCHESTRATOR=16
OC_STEPS_BUILDER=14
```

## Watchdog des sous-agents

OpenCode V1 charge `plugins/runtime-guardrails.js` via le lien symbolique global géré par :

```bash
just install-user
```

Le plugin reste volontairement inactif dans les sessions OpenCode ordinaires. Le launcher du toolkit l’active avec `OPENCODE_TOOLKIT_RUNTIME_GUARDS=1`.

Le watchdog suit chaque session enfant séparément de la session racine et distingue l’activité du progrès. Il exploite les événements de session, permissions, messages, fichiers, todos et outils sans demander au LLM « où en es-tu ? ».

Il peut arrêter un enfant lorsqu’une limite déterministe est franchie :

- erreur non retryable d’authentification/provider/configuration ;
- même erreur répétée au-delà du seuil ;
- même appel d’outil produisant plusieurs fois le même résultat ;
- absence de progrès au-delà du timeout ;
- durée maximale de l’enfant dépassée ;
- budget de coût de l’enfant dépassé lorsque OpenCode remonte le coût ;
- budget global du run dépassé lorsque OpenCode remonte le coût.

`WAITING_PERMISSION` est explicitement exclu de la détection de stagnation.

## Parallélisme configurable

`OC_MAX_PARALLEL_SUBAGENTS` est une vraie barrière de lancement. Les sous-agents supplémentaires attendent dans une file avant l’exécution du tool de délégation ; l’attente elle-même ne déclenche donc pas un appel LLM supplémentaire.

```bash
OC_MAX_PARALLEL_SUBAGENTS=3
```

Des surcharges par lead sont disponibles :

```bash
OC_MAX_PARALLEL_META_ROUTER=2
OC_MAX_PARALLEL_ORCHESTRATOR=3
OC_MAX_PARALLEL_REVIEW_LEAD=3
OC_MAX_PARALLEL_PLATFORM_ARCHITECT=3
OC_MAX_PARALLEL_SECURITY_LEAD=2
```

Le lead est identifié grâce aux hooks chat d’OpenCode. S’il n’est pas identifiable, la limite globale est utilisée.

## Profils

Trois profils donnent des valeurs initiales :

| Profil | Parallèle | Stall | Durée enfant | Coût enfant | Coût run |
| --- | ---: | ---: | ---: | ---: | ---: |
| `cheap` | 2 | 120 s | 420 s | 0.25 | 1.00 |
| `normal` | 3 | 180 s | 600 s | 0.50 | 2.00 |
| `premium` | 4 | 240 s | 900 s | 1.50 | 5.00 |

Les valeurs de coût utilisent l’unité remontée par OpenCode/provider, généralement l’USD. Le coût est une barrière supplémentaire, jamais la seule : si un provider ne remonte pas le coût, les limites de steps, durée, parallélisme, répétition d’erreurs et stagnation restent actives.

Choix du profil :

```bash
OC_RUNTIME_PROFILE=normal
```

Les variables `OC_*` explicites prennent le dessus sur le profil.

## Checkpoints

Le watchdog écrit des checkpoints de métadonnées sous :

```text
${XDG_STATE_HOME:-~/.local/state}/opencode-agent-toolkit/runs/<session-id>.json
```

Ils contiennent l’ID de session enfant, son parent, son agent, son état, la raison d’arrêt, le coût remonté et les timestamps d’activité/progrès. Les prompts et le contenu du code ne sont pas recopiés dans ce dossier. La session OpenCode reste la source de vérité pour reprendre le travail détaillé.

## Supervision par les leads

Les cinq leads reçoivent des instructions supplémentaires pour :

- respecter la file de parallélisme sans la contourner ;
- ne pas confondre activité répétée et progrès réel ;
- consommer les preuves/checkpoints d’un enfant bloqué ou interrompu avant de le remplacer ;
- reprendre depuis le dernier gate terminé au lieu de recommencer tout le workflow ;
- ne jamais dupliquer un enfant encore actif ;
- distinguer l’attente de permission d’un véritable stall.

La séparation importante est : **les LLM prennent les décisions d’ingénierie ; le code déterministe impose les limites de sécurité du runtime.**

## Commandes

```bash
just install-user   # installe/met à jour le launcher et le watchdog
just preflight      # vérifie sans démarrer de session modèle
just doctor         # affiche les limites et l’installation du watchdog
just check          # régénère les configs bornées et lance les tests
```

## Note OpenCode V2

Le watchdog complet actuel cible l’API plugin V1 stable utilisée par défaut par le toolkit. V2 reçoit tout de même les limites de steps et les règles de supervision des leads, mais le plugin V1 n’est pas chargé dans V2. `preflight` affiche explicitement ce mode dégradé au lieu de faire croire que le watchdog runtime est actif.
