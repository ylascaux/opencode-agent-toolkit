# OpenCode Agent Toolkit — OpenCode 2

> **Branches de version**
>
> - `v1` : version actuelle figée du toolkit.
> - `main` : développement **V2**.
>
> La conception V2 est documentée dans [`docs/v2/`](docs/v2/README.md). Les premières évolutions structurantes sont une mémoire partagée multi-machine via PostgreSQL et une couche de runners ACP, inspirées de harness-memory/Octop sans intégrer Octop comme runtime et sans migration des données mémoire V1.


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
3. installe et construit la version pinée de `opencode-memory-plugin` (extracteur automatique) ;
4. prépare le runtime Python V2 isolé avec `harness-memory` ;
5. initialise la mémoire V2 locale par défaut (SQLite, vide, sans migration V1) ;
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

## Mémoire V2 : locale ou partagée

La V2 utilise `harness-memory` comme source de vérité. Une installation neuve démarre avec un SQLite local :

```text
oc
 ├── opencode-memory-plugin       # extraction automatique session idle
 ├── oat-memory MCP              # recherche/rendu/proposition
 └── harness-memory
       ├── local SQLite (défaut)
       └── PostgreSQL (multi-PC)
```

Aucune donnée de la V1 n'est migrée. L'ancien backend Git reste disponible uniquement avec `OAT_MEMORY_BACKEND=legacy` ou via la branche `v1`.

Pour partager la même mémoire entre deux PC, exécute sur chacun :

```bash
git pull
just install
oc memory configure-postgres 'postgresql://USER:PASSWORD@HOST:5432/DB'
oc memory status
```

L'identité du projet est dérivée du remote Git canonique, donc deux clones de `owner/repo` utilisent le même namespace :

```text
oat:project:owner/repo
oat:user:default
```

La capture reste automatique. Les faits projet, architecture, décisions et conventions vont dans le namespace projet ; les préférences de travail vont dans le namespace utilisateur partagé.

Commandes utiles :

```bash
oc memory status
oc memory namespace
oc memory show
oc memory add decision "Titre" "Information durable"
oc memory configure-local
oc memory configure-postgres 'postgresql://...'
```

Le DSN PostgreSQL reste dans l'environnement local et n'est jamais sérialisé dans la configuration OpenCode générée.

Documentation détaillée : [docs/v2/shared-memory.md](docs/v2/shared-memory.md).

## ACP et jobs parallèles

OpenCode reste le runtime principal. La V2 ajoute un manager ACP via le MCP `oat-acp`.

Les agents leads peuvent utiliser `acp_runner` pour un travail indépendant/long ou un runtime ACP alternatif :

```text
start → status → [permission_required → respond] → completed → close
```

Les jobs sont exécutés dans un pool borné (`OAT_ACP_MAX_PARALLEL=4` par défaut). Chaque child utilise son propre processus `opencode acp`, reste dans le workspace parent et ne reçoit ni le DSN mémoire ni les MCP `oat-memory` / `oat-acp`.

Inspection humaine :

```bash
oc runner list
oc runner doctor
oc runner command opencode
```

Documentation détaillée : [docs/v2/acp-runners.md](docs/v2/acp-runners.md).

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
