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
OAT_AI_MEMORY_REPO=git@github.com:ylascaux/opencode-memory.git
```

Si le clone n'existe pas encore, `just install` le clone. Un clone existant
n'est ni remplacé ni automatiquement pullé.

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
