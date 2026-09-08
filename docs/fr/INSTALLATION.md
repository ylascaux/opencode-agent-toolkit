# Installation

Le toolkit utilise `just` comme interface principale pour les commandes du quotidien.

## Installation macOS recommandée

```bash
brew install just
git clone https://github.com/ylascaux/opencode-agent-toolkit.git
cd opencode-agent-toolkit
just install
```

`just install` effectue tout le bootstrap :

1. crée `.env` depuis `.env.example` s’il n’existe pas ;
2. conserve un `.env` existant ;
3. crée `.venv` ;
4. installe les dépendances du CLI/API d’inventaire ;
5. génère les configurations natives OpenCode V1 et V2 ;
6. valide les deux configurations ;
7. exécute les tests du repository ;
8. vérifie le runtime OpenCode sélectionné.

La commande ne remplace pas automatiquement un mapping de modèles déjà configuré.

## Sans `just`

Le script de bootstrap ne dépend pas de `just` :

```bash
./scripts/bootstrap
./scripts/opencode-agents
```

## Configurer les modèles

Par défaut, tous les agents utilisent `litellm/smart-router`. Tu peux ensuite spécialiser uniquement les rôles importants :

```dotenv
MODEL_META_ROUTER=litellm/fast-router
MODEL_ORCHESTRATOR=litellm/smart-router
MODEL_BUILDER=litellm/coding-model
MODEL_REVIEWER=litellm/reasoning-model
MODEL_DEEP_REASONER=litellm/deep-reasoning-model
MODEL_APPSEC=litellm/security-review-model
```

Afficher le mapping courant :

```bash
just models
```

## Choix du runtime

Dans `.env` :

```dotenv
OPENCODE_MAJOR=1
```

Valeurs :

- `1` : `opencode` stable avec `opencode.jsonc` ;
- `2` : OpenCode 2 beta `opencode2` avec `opencode.v2.jsonc` ;
- `auto` : préfère `opencode2` s’il existe, sinon `opencode`.

Forcer une version pour une seule exécution :

```bash
just v1
just v2
```

## Commandes quotidiennes

```bash
just                 # liste les recettes
just install         # installation initiale
just doctor          # diagnostic environnement/config
just run             # lance le runtime sélectionné
just v1              # force OpenCode V1
just v2              # force OpenCode V2
just check           # génère/valide les configs + tests
just test            # tests du repository
just scan            # crée architecture-inventory.json
just api             # démarre l’API locale d’inventaire
just models          # affiche les mappings MODEL_*
just refresh         # recrée le venv et les dépendances
just clean           # supprime l’état local généré
```

## Diagnostic

```bash
just doctor
```

Le diagnostic vérifie Python, `just`, les binaires OpenCode, `.env`, `.venv`, la validité V1/V2, les tests, `PROJECTS_ROOT`, le runtime choisi ainsi que le nombre d’agents et de commandes.

Les avertissements liés aux composants optionnels, comme OpenCode 2 ou un dossier `~/Projects` absent, ne sont pas bloquants.
