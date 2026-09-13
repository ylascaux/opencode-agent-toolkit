# Installation

`just` est l’interface principale.

## Installation rapide macOS

Prérequis : Bash, Python 3.11+, `just` et le runtime natif à utiliser : `opencode` pour V1 ou `opencode2` pour V2. Installe le runtime avec sa procédure officielle ; le toolkit ne l’installe pas et ne migre pas l’authentification.

```bash
brew install just
git clone https://github.com/ylascaux/opencode-agent-toolkit.git
cd opencode-agent-toolkit
just install
just doctor
```

`just install` crée `.env` seulement s’il n’existe pas, génère les deux configurations OpenCode natives et installe les lanceurs `oc` et `oc2` dans `~/.local/bin`. Ajoute toi-même ce répertoire à `PATH` si nécessaire.

Il n’installe **aucun paquet**, n’utilise pas `sudo`, ne modifie pas les fichiers de démarrage du shell, ne touche pas à `~/.config`, ne contacte pas de provider et ne démarre pas de serveur en arrière-plan.

## Profil de modèles par défaut

Le profil de travail par défaut est GitHub Copilot :

```text
LOW    -> github-copilot/gpt-5.6-luna
MEDIUM -> github-copilot/gpt-5.6-terra
HIGH   -> github-copilot/gpt-5.6-sol
```

Vérifie les modèles réellement exposés à ton compte :

```bash
opencode models github-copilot
```

Si les IDs diffèrent, édite `profiles/copilot.env.example` puis réapplique le profil :

```bash
just profile copilot
```

## Changer de provider / profil perso

```bash
just profile copilot
just profile codex
```

Le changement de profil met à jour `MODEL_PROFILE`, `MODEL_LOW`, `MODEL_MEDIUM` et `MODEL_HIGH` dans `.env`. Il retire aussi les mappings `MODEL_*` historiques par agent de `.env` et les sauvegarde dans `.env.model-overrides.backup`.

Les overrides persistants par agent doivent être placés dans `.env.local`, qui n’est jamais modifié par un changement de profil :

```bash
MODEL_BUILDER=openai/gpt-5.3-codex
MODEL_REVIEWER=github-copilot/gpt-5.6-sol
```

## Lancer depuis n’importe où

`just install` installe les liens gérés par le toolkit :

```text
~/.local/bin/oc -> <toolkit>/scripts/opencode-agents
~/.local/bin/oc2 -> <toolkit>/scripts/opencode-agents
```

Le launcher conserve le répertoire courant :

```bash
cd ~/Projects/my-api
oc
```

OpenCode utilise `~/Projects/my-api` comme workspace tout en chargeant la configuration et les modèles depuis le toolkit.

Supprimer proprement les liens gérés par le toolkit :

```bash
just uninstall
```

L’installateur n’écrase jamais un fichier ou symlink appartenant à autre chose et ne modifie jamais ton shell. `just uninstall` ne retire que les liens `oc` et `oc2` appartenant à ce toolkit.

## Choix du runtime

Utilise `oc` pour OpenCode V1 et `oc2` pour OpenCode V2. Les deux conservent le répertoire courant comme workspace. Définis `OPENCODE_BIN` pour utiliser un chemin explicite vers le binaire du runtime.


## Recettes quotidiennes

```bash
just install
just profile copilot
just config
just doctor
just test
just uninstall
```
