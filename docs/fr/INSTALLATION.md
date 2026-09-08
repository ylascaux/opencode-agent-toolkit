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
