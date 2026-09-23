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

## Plugin mémoire

La configuration générée charge uniquement le plugin mémoire tiers :

```text
opencode-mem@2.26.0
```

OpenCode 2 installe automatiquement le package configuré et ses dépendances.
Le plugin fournit mémoire locale par projet, recherche vectorielle, auto-capture
et réinjection de souvenirs.

Au premier lancement, si
`~/.config/opencode/opencode-mem.jsonc` n'existe pas, le toolkit crée une
configuration minimale. Le provider est déduit du profil `MODEL_*` actif et
`opencodeModel` vaut `inherit`. Une configuration existante n'est jamais écrasée.

Pour forcer le provider utilisé par l'auto-capture :

```bash
# .env.local
OAT_MEMORY_PROVIDER=github-copilot
```

Le premier usage des embeddings locaux peut télécharger le modèle nécessaire.

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
