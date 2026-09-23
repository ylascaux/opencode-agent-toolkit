# Installation

Le toolkit cible uniquement **OpenCode 2 stable**. La commande utilisateur est
`oc`, qui lance le binaire officiel `opencode`.

## Installation rapide macOS

Prérequis : Bash, Python 3.11+, `just` et npm.

```bash
brew install just
git clone https://github.com/ylascaux/opencode-agent-toolkit.git
cd opencode-agent-toolkit
just install
just doctor
```

`just install` met à jour OpenCode avec `@opencode/cli@latest`, retire
l'ancien paquet `opencode-ai`, génère la configuration stable et installe
`opencode-mem@2.26.0` avec `opencode plugin add`.

Il installe uniquement :

```text
~/.local/bin/oc -> <toolkit>/scripts/opencode-agents
```

Un ancien lien toolkit `oc2` est supprimé automatiquement.

## Gérer OpenCode ailleurs

Si OpenCode est installé par Homebrew ou une autre méthode :

```bash
OAT_INSTALL_OPENCODE=0 just install
```

Pour ne pas installer/mettre à jour les plugins :

```bash
OAT_INSTALL_PLUGINS=0 just install
```

## Profil de modèles par défaut

```text
LOW    -> github-copilot/gpt-5.6-luna
MEDIUM -> github-copilot/gpt-5.6-terra
HIGH   -> github-copilot/gpt-5.6-sol
```

Changer de profil :

```bash
just profile copilot
just profile codex
```

Les overrides persistants par agent appartiennent à `.env.local`.

## Utilisation

```bash
cd ~/Projects/my-api
oc
oc run "Lance les tests"
oc plugin list
```

Le répertoire courant reste le workspace OpenCode.

## Diagnostic

```bash
just doctor
opencode --version
opencode plugin list
opencode plugin check
```

`just uninstall` retire uniquement les liens gérés par le toolkit. Il ne
supprime ni OpenCode, ni son authentification, ni ses plugins.
