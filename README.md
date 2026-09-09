# OpenCode Agent Toolkit

Un toolkit multi-agents pour [OpenCode](https://opencode.ai/) : il génère une configuration V1/V2 à partir d'agents autonomes, applique des garde-fous de fiabilité et de permissions, puis fournit un lanceur et des diagnostics pour travailler sur un projet.

Le plan de contrôle reste volontairement court : `meta-router -> lead -> specialist`. Les agents vivent dans `agents/<nom>/` et déclarent eux-mêmes leur rôle, leurs parents autorisés et leurs permissions.

## Démarrer en cinq minutes

Prérequis : Git, Bash, Python 3, Node.js, OpenCode, et [`just`](https://github.com/casey/just). Sur macOS : `brew install just`.

```bash
git clone https://github.com/ylascaux/opencode-agent-toolkit.git
cd opencode-agent-toolkit
just install
just models
just doctor
just run
```

`just install` crée `.env` s'il est absent, prépare l'environnement Python, installe les dépendances locales du scanner/API, génère et valide les configurations OpenCode, puis lance les tests **Python**. Pour la validation complète (génération, tests Python et tests Node), exécutez `just check`.

Les configurations générées sont `opencode.jsonc` (V1) et `opencode.v2.jsonc` (V2). Pour OpenCode 2, utilisez `just v2` ou installez le lanceur dédié avec `just install-oc2` puis lancez `oc2 .`.

## Repères rapides

```bash
just config                  # régénère les configurations localement
just check                   # validation complète : config + Python + Node
just agents                  # inspecte les agents et leur topologie
just new-agent mon-agent --parent orchestrator
just run                     # lance OpenCode avec la configuration active
just configure-litellm       # découverte LiteLLM, optionnelle
```

Les overrides par agent doivent aller dans `.env.local`, afin de ne pas être écrasés par `just profile`.

## Mémoire Git privée optionnelle

Le toolkit peut charger une mémoire long terme depuis un dépôt Git privé, avec contexte par projet, préférences de travail et casquettes par agent. Cette mémoire est **désactivée par défaut** et reste en lecture seule côté agents.

```bash
just memory-on git@github.com:USER/opencode-memory.git
just memory-status
just memory-show orchestrator
```

Le clone mémoire n'est pas monté dans la sandbox : seul le contexte rendu est injecté dans les prompts générés. Voir [la documentation mémoire](docs/fr/MEMORY.md).

## Toutes les recettes `just`

Sans argument, `just` exécute `default`, qui affiche cette liste (`just --list`). Les paramètres entre guillemets indiquent leur valeur par défaut ; `*args` transmet des arguments supplémentaires.

### Installation, profils et diagnostics

| Recette | Syntaxe | Description |
| --- | --- | --- |
| `default` | `just` | Affiche les recettes disponibles. |
| `install` | `just install` | Initialisation locale, génération des configs et tests Python. |
| `refresh` | `just refresh` | Relance l'initialisation en mode actualisation. |
| `profile` | `just profile [name="copilot"]` | Applique un profil de modèles. Les overrides persistants restent dans `.env.local`. |
| `profiles` | `just profiles` | Liste les profils de modèles disponibles. |
| `models` | `just models` | Affiche la résolution effective des modèles. |
| `doctor` | `just doctor` | Diagnostique les prérequis et la configuration locale. |
| `configure-litellm` | `just configure-litellm [args…]` | Découvre des modèles LiteLLM et crée des mappings explicites ; optionnel, jamais appelé par `config`. |

### Agents et configuration

| Recette | Syntaxe | Description |
| --- | --- | --- |
| `agents` | `just agents` | Liste les agents découverts dans `agents/<nom>/`. |
| `new-agent` | `just new-agent <name> [args…]` | Crée le squelette d'un agent autonome. |
| `config` | `just config` | Génère les configs V1/V2, applique la politique de fiabilité et vérifie leur JSON. Aucun appel fournisseur ni prompt interactif. |
| `preflight` | `just preflight` | Vérifications déterministes avant un lancement OpenCode ; requiert `.env`. |
| `reliability` | `just reliability` | Affiche la politique de fiabilité effective, overrides compris. |
| `check` | `just check` | Validation complète : `config`, tests Python et tests Node de runtime. |
| `test` | `just test` | Exécute la suite de tests Python. |
| `runtime-test` | `just runtime-test` | Exécute les tests Node du comportement runtime. |

### Lancer OpenCode et outils de projet

| Recette | Syntaxe | Description |
| --- | --- | --- |
| `run` | `just run [args…]` | Lance OpenCode avec la version/configuration active. |
| `v1` | `just v1 [args…]` | Lance OpenCode V1 explicitement. |
| `v2` | `just v2 [args…]` | Lance OpenCode V2 explicitement. |
| `serve` | `just serve [args…]` | Démarre un serveur OpenCode headless avec la version active. |
| `serve-v2` | `just serve-v2 [args…]` | Démarre explicitement un serveur OpenCode 2 headless. |
| `scan` | `just scan [args…]` | Analyse des projets et écrit `architecture-inventory.json`. |
| `api` | `just api` | Lance l'API d'inventaire. |

### Lanceurs utilisateur

| Recette | Syntaxe | Description |
| --- | --- | --- |
| `install-user` | `just install-user [command="oc"]` | Installe un lanceur réversible dans `~/.local/bin`. |
| `uninstall-user` | `just uninstall-user [command="oc"]` | Retire ce lanceur s'il pointe vers ce toolkit. |
| `user-status` | `just user-status [command="oc"]` | Indique si le lanceur utilisateur pointe vers ce toolkit. |
| `install-oc2` | `just install-oc2` | Installe le lanceur V2 dédié `oc2`. |
| `uninstall-oc2` | `just uninstall-oc2` | Retire le lanceur dédié `oc2`. |
| `oc2-status` | `just oc2-status` | Indique si `oc2` est installé. |

### Mémoire long terme

| Recette | Syntaxe | Description |
| --- | --- | --- |
| `memory-on` | `just memory-on [repo=""]` | Active la mémoire Git et peut enregistrer l'URL du dépôt privé dans `.env.local`. |
| `memory-off` | `just memory-off` | Désactive la mémoire et supprime le contexte rendu. |
| `memory-status` | `just memory-status` | Affiche la configuration effective et le projet mémoire détecté. |
| `memory-sync` | `just memory-sync` | Force le clone/pull du dépôt mémoire et reconstruit le contexte. |
| `memory-show` | `just memory-show [agent="orchestrator"]` | Affiche le contexte commun et les casquettes injectés pour un agent. |

### Sandbox et maintenance

| Recette | Syntaxe | Description |
| --- | --- | --- |
| `sandbox-build` | `just sandbox-build` | Construit l'image Nix durcie avec Docker ou Podman. |
| `sandbox-on` | `just sandbox-on` | Construit l'image puis active l'exécution shell sandboxée dans `.env.local`. |
| `sandbox-off` | `just sandbox-off` | Désactive la sandbox sans supprimer son image. |
| `sandbox-doctor` | `just sandbox-doctor` | Vérifie la politique sandbox, le filtrage cloud et le runtime/image local. |
| `sandbox-clean` | `just sandbox-clean` | Supprime les conteneurs sandbox orphelins, sans supprimer l'image. |
| `clean` | `just clean` | Supprime `.venv`, `.generated` et `architecture-inventory.json`. |

## Documentation détaillée

- [Documentation française](docs/fr/README.md) : installation, agents, permissions, modèles, fiabilité, sandbox et usage.
- [Index de la documentation anglaise](docs/en/README.md).
- [Architecture système](docs/fr/SYSTEM_ARCHITECTURE.md), [configuration des agents](docs/fr/CONFIGURATION_AGENTS.md) et [mémoire Git](docs/fr/MEMORY.md).
- [Gates de qualité de contribution](workflows/quality-gates.md).

Les contrats machine lisibles sont dans [`contracts/`](contracts/), notamment `agent-handoff.schema.json` et `routing-decision.schema.json`.
