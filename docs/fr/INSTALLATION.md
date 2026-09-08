# Installation

`just` est l’interface principale.

## Installation rapide macOS

```bash
brew install just
git clone https://github.com/ylascaux/opencode-agent-toolkit.git
cd opencode-agent-toolkit
just install
just doctor
```

`just install` crée `.env` seulement s’il n’existe pas, crée `.venv`, installe les dépendances du scanner/API, génère les deux configurations OpenCode, les valide et lance les tests.

Il n’installe **aucun paquet global**, n’utilise pas `sudo`, ne modifie pas les fichiers de démarrage du shell et ne touche pas à `~/.config`.

## Commande utilisateur optionnelle : lancer depuis n’importe où

`just run` fonctionne depuis le repo du toolkit. Pour un usage quotidien dans plusieurs repos, installe la commande réversible `oc` :

```bash
just install-user
```

Cela crée uniquement :

```text
~/.local/bin/oc -> <toolkit>/scripts/opencode-agents
```

Le launcher ne fait pas de `cd` dans le toolkit. Le répertoire courant est conservé :

```bash
cd ~/Projects/my-api
oc
```

OpenCode utilise alors `~/Projects/my-api` comme workspace tout en chargeant la configuration et les mappings de modèles depuis le repo du toolkit.

Vérifier le lien :

```bash
just user-status
```

Le supprimer proprement :

```bash
just uninstall-user
```

La désinstallation ne supprime le chemin que s’il s’agit bien d’un symlink pointant vers ce toolkit. Un fichier ou lien appartenant à autre chose n’est jamais écrasé ni supprimé.

Si `oc` existe déjà sur la machine, choisis un autre nom :

```bash
just install-user opencode-agents
```

Le répertoire cible par défaut est `~/.local/bin`. Tu peux le changer sans modifier automatiquement ton shell :

```bash
OPENCODE_TOOLKIT_BIN_DIR="$HOME/bin" just install-user
```

Si le répertoire choisi n’est pas dans `PATH`, l’installateur affiche seulement un avertissement ; il ne modifie jamais ton shell automatiquement.

Si tu déplaces ensuite le repo du toolkit, exécute `just uninstall-user` avant le déplacement puis `just install-user` après afin de recréer le symlink vers le nouveau chemin.

## Configurer automatiquement les modèles

```bash
export LITELLM_BASE_URL="https://gateway.example.com"
export LITELLM_API_KEY="..."
just configure
```

Le configurateur interroge `/v1/models`, recommande les profils `fast`, `general`, `coding`, `reasoning`, `deep`, `review` et `security`, puis mappe ces profils vers les 37 variables `MODEL_*`. Les choix sont modifiables interactivement.

Mode non interactif : `just configure --auto`

Simulation : `just configure --auto --dry-run`

Depuis une réponse enregistrée : `just configure --models-file ./models.json`

### Cloudflare Access / headers personnalisés

```bash
export CF_ACCESS_TOKEN="..."
export LITELLM_HEADERS_JSON='{"x-custom-header":"value"}'
just configure
```

`CF_ACCESS_TOKEN` est envoyé dans `cf-access-token`. Les clés API et tokens Access ne sont jamais écrits dans `.env` par le configurateur.

## Choix du runtime

`OPENCODE_MAJOR` accepte `1`, `2` ou `auto`. `just v1` et `just v2` permettent un override ponctuel.

## Recettes quotidiennes

```bash
just install
just install-user
just user-status
just uninstall-user
just configure
just doctor
just run
just check
just test
just scan
just api
just models
just refresh
just clean
```
