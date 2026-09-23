# OpenCode Agent Toolkit — OpenCode 2

Le toolkit cible désormais uniquement **OpenCode 2 stable**.

Il n'y a plus de runtime `oc2`, de binaire `opencode2`, ni de double
configuration V1/V2. La commande quotidienne est simplement :

```bash
oc
```

Le wrapper `oc` lance le binaire officiel `opencode` et conserve le catalogue
d'agents, les modèles par niveau, les skills et la synchronisation Codex.

## Installation / mise à jour

Prérequis : Bash, Python 3.11+, Zsh et `just`. npm est requis pour installer `create-ai-memory` (sauf si `OAT_AI_MEMORY_HOME` pointe déjà vers une installation valide) et pour OpenCode uniquement si le binaire `opencode` est absent.

```bash
git pull
just install
just doctor
```

`just install` :

1. si `opencode` existe déjà dans le PATH, **ne touche pas à cette installation** ;
2. sinon, installe `@opencode/cli@latest` avec npm ;
3. installe la version pinée de `create-ai-memory` dans les données utilisateur du toolkit si nécessaire ;
4. clone `opencode-memory` seulement si le vault local n'existe pas ;
5. génère `opencode.jsonc` au format natif OpenCode 2 ;
6. installe uniquement `~/.local/bin/oc` ;
7. supprime l'ancien lien toolkit `~/.local/bin/oc2` s'il existe.

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

## Mémoire persistante : create-ai-memory + opencode-memory

Le toolkit utilise directement le package upstream :

```text
create-ai-memory@0.15.4
```

Il n'est ni forké ni ajouté comme submodule. `just install` l'installe dans un
répertoire utilisateur géré par le toolkit :

```text
~/.local/share/opencode-agent-toolkit/vendor/ai-memory/
```

Le vault reste séparé dans le repo Git/Obsidian :

```text
~/opencode-memory/
├── projects/
├── sessions/
├── lessons/
├── workstyle/
├── hats/
├── inbox/
└── templates/
```

Par défaut le toolkit utilise :

```bash
OAT_AI_MEMORY_ROOT=$HOME/opencode-memory
OAT_AI_MEMORY_REPO=https://github.com/ylascaux/opencode-memory.git
```

Si le clone n'existe pas encore, `just install` le clone. Pour un repo privé GitHub, Git doit être authentifié (par exemple avec `gh auth login` puis `gh auth setup-git`). Un clone existant n'est ni remplacé ni automatiquement pullé.

### Compatibilité avec create-ai-memory

L'upstream attend des noms comme `_projects/`, `_session_logs/`,
`_lessons/`, `_Global_Profile.md` et `_Standards.md`. Le toolkit crée une
vue de compatibilité locale sans changer l'organisation réelle du vault :

```text
_Global_Profile.md  -> workstyle/preferences.md
_Standards.md       -> workstyle/engineering.md
_session_logs       -> sessions/
_lessons            -> lessons/
_projects/<repo>.md -> projects/<repo>/context.md
```

Ces liens sont ajoutés à `.git/info/exclude`, donc ils ne polluent pas le repo.
Les vraies notes, sessions et leçons restent dans les dossiers lisibles dans
Obsidian et versionnables avec Git.

Le projet courant est résolu depuis le repo Git actif et, quand il existe,
`projects/index.json` peut mapper un nom de repo ou un remote vers un identifiant
de mémoire différent.

### Intégration OpenCode

Au lancement de `oc` :

1. le projet courant est identifié ;
2. create-ai-memory prépare le contexte global + projet + dernière session ;
3. ce contexte est injecté dans les instructions OpenCode ;
4. un serveur MCP local `oat-memory` est ajouté pour la session.

Les outils MCP exposés sont :

```text
search_memory
get_context
read_note
add_note
add_lesson
memory_status
```

Ainsi OpenCode peut chercher dans tout le vault, ajouter une note à la session
courante ou créer une leçon transverse sans utiliser `opencode-start`.

Le package upstream reste la source de vérité pour la logique de contexte,
recherche, notes, leçons et backup Git. L'adaptateur du toolkit ne réimplémente
pas ces règles ; il mappe seulement ton layout et les expose proprement à
OpenCode 2.

### Désactivation / versions

```bash
# .env.local
OAT_AI_MEMORY_ENABLED=0

# ou pour tester une autre version upstream
OAT_AI_MEMORY_VERSION=0.15.4
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
