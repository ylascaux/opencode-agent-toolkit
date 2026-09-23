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

Prérequis : Bash, Python 3.11+ et `just`. npm n'est requis que si `opencode` n'est pas déjà installé.

```bash
git pull
just install
just doctor
```

`just install` :

1. si `opencode` existe déjà dans le PATH, **ne touche pas à cette installation** ;
2. sinon, installe `@opencode/cli@latest` avec npm ;
3. génère `opencode.jsonc` au format natif OpenCode 2 ;
4. installe uniquement `~/.local/bin/oc` ;
5. supprime l'ancien lien toolkit `~/.local/bin/oc2` s'il existe.

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

## Mémoire Markdown : Obsidian + Git

Le toolkit utilise désormais :

```text
oc2-memory@0.1.1
```

Le nom du package est historique : il cible bien **OpenCode 2** et utilise l'API
native `@opencode/plugin` 2.x.

La mémoire est stockée en fichiers Markdown simples :

```text
MEMORY.md
SCRATCHPAD.md
daily/YYYY-MM-DD.md
recovery/*.json
```

Il n'y a pas de base vectorielle obligatoire. La recherche fonctionne en mode
keyword sans dépendance supplémentaire. `qmd` peut être installé séparément si
vous voulez ajouter recherche sémantique/hybride.

Pour choisir l'emplacement de la mémoire :

```bash
# .env.local
OAT_MARKDOWN_MEMORY_DIR="/chemin/vers/MonVault/OpenCodeMemory"
```

Le même dossier peut être :

- un sous-dossier d'un vault **Obsidian** ;
- un **repo Git** ;
- ou les deux à la fois, ce qui est le mode conseillé si vous voulez une mémoire
  lisible dans Obsidian et synchronisée/versionnée par Git.

Si aucune variable n'est configurée, le plugin utilise son stockage local par
défaut.

### Rehydra

`@rehydra/opencode` n'est plus utilisé par le toolkit. `just install` demande
aussi à OpenCode de retirer son entrée globale si elle existe, et la configuration
du toolkit désactive les IDs `rehydra` / `rehydra.*` provenant d'une
configuration de priorité inférieure.


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
