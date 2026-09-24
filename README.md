# OpenCode Agent Toolkit — OpenCode 2

> **Branches de version**
>
> - `v1` : version actuelle figée du toolkit.
> - `main` : développement **V2**.
>
> La conception V2 est documentée dans [`docs/v2/`](docs/v2/README.md). La première évolution structurante prévue est une mémoire partagée multi-machine via PostgreSQL, inspirée de harness-memory/Octop, sans intégrer Octop comme runtime et sans migration des données mémoire V1.


Le toolkit cible désormais uniquement **OpenCode 2 stable**.

Il n'y a plus de runtime `oc2`, de binaire `opencode2`, ni de double
configuration V1/V2. La commande quotidienne est simplement :

```bash
oc
```

Le wrapper `oc` lance le binaire officiel `opencode` et conserve le catalogue
d'agents, les modèles par niveau, les skills et la synchronisation Codex.

## Installation / mise à jour

Prérequis : Bash, Python 3.11+, Git, Node.js et `just`. npm n'est requis pour OpenCode que si le binaire `opencode` est absent.

```bash
git pull
just install
just doctor
```

`just install` :

1. si `opencode` existe déjà dans le PATH, **ne touche pas à cette installation** ;
2. sinon, installe `@opencode/cli@latest` avec npm ;
3. clone/réutilise le vault privé `~/opencode-memory` ;
4. installe et construit la version pinée de `opencode-memory-plugin` dans les données utilisateur du toolkit ;
5. migre automatiquement l'ancien bloc `OAT_AI_MEMORY_*` s'il provient de l'intégration temporaire `create-ai-memory` ;
6. génère `opencode.jsonc` au format natif OpenCode 2 ;
7. installe uniquement `~/.local/bin/oc` et retire l'ancien lien `oc2`.

L'authentification OpenCode reste dans le stockage natif du CLI et n'est pas
réinitialisée par le toolkit.

Depuis n'importe quel projet :

```bash
oc
oc run "Corrige le bug et lance les tests"
oc auth list
oc auth login
oc models
oc plugin list
```

Les invocations interactives et `run` utilisent `--standalone` par défaut afin
qu'un ancien service OpenCode en arrière-plan ne conserve pas une configuration
obsolète. Les commandes serveur/service et un `--server` explicite sont respectés.

## Catalogue d'agents minimal

Le runtime charge volontairement **9 agents actifs** au lieu d'exposer les 41 profils historiques :

| Agent | Rôle | Tier |
| --- | --- | --- |
| `meta-router` | classification et routage minimal | MEDIUM |
| `orchestrator` | livraison multi-étapes et coordination | HIGH |
| `builder` | implémentation générale | MEDIUM |
| `debugger` | diagnostic et root cause | MEDIUM |
| `tester` | tests comportementaux/régression | MEDIUM |
| `reviewer` | review indépendante | HIGH |
| `platform-architect` | architecture plateforme/cloud | HIGH |
| `security-lead` | sécurité transverse | HIGH |
| `research-runner` | docs actuelles / Context7 / recherche | MEDIUM |

Les spécialisations Go, Python, Terraform, Kubernetes, AWS, CI/CD, AppSec, IAM, observabilité, FinOps, etc. sont traitées comme des **compétences** des agents principaux plutôt que comme des identités d'agents permanentes.

La communication reste structurée : un agent enfant renvoie un handoff à son parent et peut demander un agent suivant. Le parent décide de la délégation et transmet un état de mission compact (décisions, artefacts, preuves, questions ouvertes, risques). Il n'y a pas de conversation libre agent-à-agent ni de chaîne de délégation non bornée.

## Documentation actuelle : Context7

Context7 est activé par défaut comme MCP distant natif OpenCode 2 :

```text
https://mcp.context7.com/mcp
```

Aucun package Context7 n'est installé localement et aucune version du plugin
OpenCode n'est à maintenir. Le toolkit ajoute également le skill
`context7-docs`, qui demande aux agents d'utiliser Context7 automatiquement
quand une tâche dépend d'une API, bibliothèque ou framework susceptible d'avoir
évolué.

Une clé API est facultative. Pour des limites plus élevées :

```bash
# .env.local
CONTEXT7_API_KEY="..."
```

La clé n'est jamais copiée dans la configuration générée : OpenCode reçoit
uniquement `{env:CONTEXT7_API_KEY}`.

Pour désactiver Context7 :

```bash
OAT_CONTEXT7_ENABLED=0
```

Une définition `context7` déjà fournie par l'utilisateur dans
`OPENCODE_CONFIG_CONTENT.mcp.servers` reste prioritaire et n'est jamais
écrasée.

## Mémoire persistante : opencode-memory-plugin + opencode-memory

Le runtime mémoire quotidien est désormais unique :

```text
oc
 ├── opencode-memory-plugin
 │    ├── contexte projet/workstyle/hats
 │    ├── capture automatique sur session.idle
 │    └── extraction de candidats mémoire
 ├── oat-memory MCP
 └── ~/opencode-memory (Git/Markdown/Obsidian)
```

Le plugin est versionné séparément et installé dans :

```text
~/.local/share/opencode-agent-toolkit/plugins/opencode-memory-plugin/
```

Le vault reste lisible et indépendant du runtime :

```text
~/opencode-memory/
├── projects/
├── workstyle/
├── hats/
├── inbox/
├── sessions/      # ancien contenu conservé, non requis par le nouveau runtime
├── lessons/
└── templates/
```

Configuration par défaut :

```bash
OAT_MEMORY_ENABLED=1
OAT_MEMORY_CAPTURE_ENABLED=1
OAT_MEMORY_AUTO_PROMOTE=1
OAT_MEMORY_AUTO_PUSH=1
OAT_MEMORY_REPO=https://github.com/ylascaux/opencode-memory.git
OAT_MEMORY_DIR=$HOME/opencode-memory
```

Au lancement de `oc`, aucun clone, pull ou build n'est effectué. Le launcher
utilise uniquement le plugin déjà installé par `just install`, rend le contexte
mémoire local et charge le plugin OpenCode 2 natif. Le même plugin expose aussi
le MCP `oat-memory`.

À chaque passage de session à l'état `idle`, le plugin lit uniquement les
messages utilisateur/assistant et extrait les informations réellement durables.

Le fonctionnement quotidien est **automatique** :

> OpenCode 2 stable envoie les événements de session via `event.data`. Le plugin mémoire suit cette enveloppe stable et associe d'abord chaque session au projet via `ctx.session.hook("prompt")`, car le flux d'événements est global.

- chaque session de travail substantielle met à jour
  `projects/<repo>/current.md`. Les analyses de dépôt peuvent en plus enrichir automatiquement `projects/<repo>/architecture.md` avec les composants, flux, dépendances, limites opérationnelles et risques architecturaux durables avec un handoff court (résumé, décisions,
  blocages, prochaine étape), même s'il n'y a aucun nouveau fait durable ;
- une mémoire `HIGH` est écrite directement dans `projects/<repo>/` ou
  `workstyle/`, commitée puis poussée vers le vault Git ;
- une information `MEDIUM` ou sans cible sûre reste en quarantaine locale ;
- si le fichier mémoire cible contient déjà des modifications locales, le plugin
  ne l'écrase pas et conserve l'élément en quarantaine ;
- des fichiers non suivis ailleurs dans le vault ne bloquent pas la capture ;
- si OpenCode est interrompu pendant l'extraction, la capture en attente est
  enregistrée localement avec le repo d'origine et reprise au prochain `oc`.

Tu n'as donc normalement **aucune commande mémoire à lancer**. Les commandes
ci-dessous restent disponibles uniquement pour le diagnostic ou les cas
ambigus :

```bash
oc memory status
oc memory trace
oc memory candidates
oc memory candidate <id>
oc memory reject <id>
```

Pour un nouveau dépôt qui n'a pas encore de dossier `projects/<repo>/`, la
capture utilise directement un identifiant stable dérivé du nom du repo et crée
le fichier durable uniquement lorsqu'une vraie mémoire HIGH est détectée.

Les fichiers `sessions/*` créés par l'intégration temporaire
`create-ai-memory` peuvent rester dans le repo : ils sont simplement ignorés
par le nouveau moteur. Il n'est pas nécessaire de les remplir ni de les
supprimer pour que la capture fonctionne.

Pour désactiver toute la mémoire :

```bash
OAT_MEMORY_ENABLED=0
```

Pour garder la lecture/contexte mais couper uniquement la capture automatique :

```bash
OAT_MEMORY_CAPTURE_ENABLED=0
```

Pour revenir au mode de validation manuelle historique :

```bash
OAT_MEMORY_AUTO_PROMOTE=0
OAT_MEMORY_AUTO_PUSH=0
```

### Rehydra

`@rehydra/opencode` n'est pas utilisé. `just install` retire son entrée
globale quand elle existe, et la configuration générée désactive aussi
`rehydra` / `rehydra.*`.


## Profils de modèles

Politique de tiers par défaut :

```text
Copilot
LOW    = github-copilot/gpt-6-luna
MEDIUM = github-copilot/gpt-6-luna
HIGH   = github-copilot/gpt-6-sol

Codex
LOW    = openai/gpt-6-luna
MEDIUM = openai/gpt-6-luna
HIGH   = openai/gpt-6-sol
```

Le niveau HIGH est réservé aux rôles où une erreur coûte cher : orchestration,
planification, review indépendante/API/evidence/supply-chain, sécurité,
architecture et raisonnement profond. Les rôles d'implémentation courants restent
en MEDIUM et utilisent donc Luna 6 par défaut.

```bash
just profile copilot
just profile codex
just config
```

Les surcharges par agent placées dans `.env.local` sont conservées.

## Codex

La synchronisation Codex reste indépendante :

```bash
oc sync codex --dry-run
oc sync codex

cd /chemin/vers/projet
oc codex install
oc codex doctor
```

Le chemin MCP mémoire historique de Codex peut encore être installé explicitement
avec `oc codex install --with-memory`. Il n'est pas utilisé par OpenCode 2.

## Commandes utiles

```bash
just install
just profile copilot
just config
just doctor
just test
just uninstall
just sync codex
just codex doctor
```

## Développement

Toute modification passe par une PR et les tests pertinents doivent être verts
avant fusion. La CI native valide le binaire publié `@opencode/cli@latest` sur
Linux et macOS.

Le mode natif n'est pas une isolation de sécurité. Les permissions précises
définies par les agents/projets restent applicables.
