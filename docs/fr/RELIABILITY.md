# Fiabilité des agents et garde-fous de coût

Le toolkit applique maintenant des protections déterministes avant et pendant l'exécution des agents. L'objectif est de détecter tôt les problèmes de configuration, de borner les boucles coûteuses et de superviser les sessions enfants sans dépendre uniquement du prompt.

## Valeurs par défaut

La politique par défaut se trouve dans `reliability.json`.

- sous-agents parallèles maximum : `3`
- délai avant détection d'un enfant bloqué : `180s`
- durée maximale d'un enfant : `900s`
- même erreur racine tolérée : `2`
- retries provider : `2`
- intervalle du watchdog : `15s`
- les caps de steps sont plus bas que les valeurs brutes du générateur ; `orchestrator` et `builder` sont limités à `16` par défaut

Toutes ces valeurs peuvent être surchargées dans `.env.local` sans modifier les fichiers versionnés.

```bash
MAX_PARALLEL_SUBAGENTS=2
SUBAGENT_STALLED_TIMEOUT_SECONDS=240
SUBAGENT_MAX_DURATION_SECONDS=1200
MAX_PROVIDER_RETRIES=1
MAX_STEPS_ORCHESTRATOR=12
MAX_STEPS_BUILDER=14
```

`just reliability` affiche la politique effective.

## Séquence de lancement

`oc` / `just run` exécute désormais :

1. chargement de `.env` et `.env.local`
2. régénération de la configuration OpenCode
3. application des caps de fiabilité et branchement du watchdog
4. résolution des tiers de modèles
5. preflight déterministe
6. démarrage d'OpenCode uniquement si le preflight passe

Le preflight peut être désactivé temporairement avec `OPENCODE_PREFLIGHT=0`. `OPENCODE_PREFLIGHT_STRICT=1` transforme les warnings en erreurs bloquantes.

## Preflight

Le preflight ne consomme aucun appel LLM. Il vérifie le binaire OpenCode sélectionné, la configuration générée, la policy de fiabilité, les variables de modèles, la limite de parallélisme, l'état Git et l'exécution de la commande d'auth OpenCode.

Les erreurs de configuration, d'authentification ou de provider détectables localement doivent donc être remontées avant de lancer une boucle de coding coûteuse.

## Watchdog des sous-agents

Les runtimes V1 et V2 utilisent chacun leur plugin watchdog.

Le watchdog suit les sessions enfants indépendamment de l'orchestrateur racine. Il distingue l'activité du progrès utile et ne considère pas `WAITING_PERMISSION` comme un blocage.

Un enfant peut être interrompu s'il dépasse sa durée maximale ou s'il ne produit plus de progrès matériel pendant le délai configuré. En V1, le watchdog coupe aussi les répétitions de la même erreur runtime/tool. En V2, il contrôle en plus les retries provider : HTTP `400`, `401`, `403` et `404` sont terminaux ; `429` et les erreurs serveur ne sont réessayés que dans la limite configurée.

## Parallélisme maximum

`MAX_PARALLEL_SUBAGENTS` fixe le nombre maximal d'enfants actifs pour une session parent. La valeur par défaut est `3`.

Le prompt de l'orchestrateur est généré avec la même valeur afin que le modèle et le garde runtime utilisent le même budget de concurrence. Si la limite est déjà atteinte, une nouvelle délégation est refusée et l'orchestrateur doit attendre qu'un enfant se termine.

Valeurs conseillées :

- `1` : modèles premium coûteux ou debug d'environnements fragiles
- `2` : mode conservateur pour une API payante
- `3` : valeur par défaut du toolkit, bon compromis pour le dev courant
- `4+` : uniquement lorsque les rate limits et le coût sont maîtrisés

## Politique d'arrêt

Les agents leads reçoivent maintenant des règles explicites : ne pas créer de chaîne de retries illimitée, réutiliser les handoffs déjà complets et distinguer `WAITING_PERMISSION` de `STALLED`.

Comportement attendu :

- erreur auth/config/permission/provider -> arrêt rapide
- `429`/`5xx` temporaire -> retry borné
- erreur code/test avec nouvelle preuve -> poursuite dans le budget de steps
- même cause racine sans nouvelle preuve -> arrêt ou une seule réorientation vers un spécialiste distinct
- enfant bloqué -> interruption, conservation des preuves, puis réorientation ou remontée du blocker

## Contrôle de coût restant

Les limites de steps, retries, durée et parallélisme bornent déjà fortement le coût. Un vrai plafond en euros nécessite cependant une télémétrie fiable du coût par requête venant du provider ou du gateway. Le toolkit ne doit appliquer un hard stop monétaire que lorsque cette donnée est autoritative ; sinon des budgets de tokens/appels/steps/temps sont plus sûrs qu'une estimation présentée comme exacte.
