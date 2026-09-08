# Installation

`just` est l’interface principale.

## Installation rapide macOS

```bash
brew install just
git clone https://github.com/ylascaux/opencode-agent-toolkit.git
cd opencode-agent-toolkit
just install
just models
just doctor
```

`just install` crée `.env` seulement s’il n’existe pas, crée `.venv`, installe les dépendances du scanner/API, génère les deux configurations OpenCode, les valide, lance les tests et vérifie la résolution des tiers de modèles.

Il n’installe **aucun paquet global**, n’utilise pas `sudo`, ne modifie pas les fichiers de démarrage du shell et ne touche pas à `~/.config`.

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
just profiles
just profile copilot
just profile codex
just models
```

Le changement de profil ne modifie que `MODEL_PROFILE`, `MODEL_LOW`, `MODEL_MEDIUM` et `MODEL_HIGH` dans `.env`.

Les overrides persistants par agent doivent être placés dans `.env.local`, qui n’est jamais modifié par un changement de profil :

```bash
MODEL_BUILDER=openai/gpt-5.3-codex
MODEL_REVIEWER=github-copilot/gpt-5.6-sol
```

## Commande utilisateur optionnelle : lancer depuis n’importe où

```bash
just install-user
```

Cela crée uniquement :

```text
~/.local/bin/oc -> <toolkit>/scripts/opencode-agents
```

Le launcher conserve le répertoire courant :

```bash
cd ~/Projects/my-api
oc
```

OpenCode utilise `~/Projects/my-api` comme workspace tout en chargeant la configuration et les modèles depuis le toolkit.

Vérifier/supprimer le lien proprement :

```bash
just user-status
just uninstall-user
```

L’installateur n’écrase jamais un fichier ou symlink appartenant à autre chose et ne modifie jamais ton shell. Si `oc` existe déjà :

```bash
just install-user opencode-agents
```

## Choix du runtime

`OPENCODE_MAJOR` accepte `1`, `2` ou `auto`. `just v1` et `just v2` permettent un override ponctuel.

## Découverte LiteLLM optionnelle

LiteLLM n’est pas requis pour l’usage normal. La découverte via gateway reste disponible pour plus tard avec :

```bash
just configure-litellm
```

L’alias `just configure` est conservé pour compatibilité.

## Recettes quotidiennes

```bash
just install
just profile copilot
just profiles
just models
just install-user
just user-status
just uninstall-user
just doctor
just run
just check
just test
just scan
just api
just refresh
just clean
```
