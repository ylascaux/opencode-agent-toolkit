# OpenCode Agent Toolkit — OpenCode 2 stable

Le toolkit utilise désormais **un seul runtime OpenCode** :

```text
oc -> opencode -> OpenCode 2 stable
```

Il n'y a plus de launcher `oc2`, plus de binaire `opencode2`, plus de
configuration V1/V2 parallèle et plus de plugins toolkit de watchdog,
plan-approval ou pricing injectés dans OpenCode.

Le catalogue d'agents, les tiers de modèles et les skills restent partagés avec
Codex.

## Installation / mise à jour

Prérequis : Bash, Python 3.11+, `just` et npm.

```bash
git pull
just install
just doctor
```

Par défaut, `just install` :

1. désinstalle l'ancien paquet `opencode-ai` ;
2. remplace toute ancienne installation `@opencode/cli` par la version stable courante ;
3. vérifie que `opencode --version` est en major 2 ;
4. génère `opencode.jsonc` au format OpenCode 2 ;
5. installe le plugin mémoire tiers `opencode-mem@2.26.0` avec le gestionnaire natif de plugins ;
6. supprime l'ancien lien toolkit `oc2` s'il existe ;
7. installe uniquement `~/.local/bin/oc`.

Si OpenCode est géré autrement, par exemple via Homebrew :

```bash
OAT_INSTALL_OPENCODE=0 just install
```

Pour ne pas toucher aux plugins pendant une installation de développement :

```bash
OAT_INSTALL_PLUGINS=0 just install
```

## Utilisation

Depuis le projet cible :

```bash
oc
oc run "Corrige le bug et lance les tests"
oc auth login
oc plugin list
oc stats --cost
```

Le launcher conserve le répertoire courant et charge la configuration du toolkit.

## Plugins

Le toolkit ne maintient plus de plugin OpenCode propriétaire.

La mémoire repose sur le plugin tiers maintenu `opencode-mem`, installé via le
gestionnaire natif OpenCode :

```bash
opencode plugin list
opencode plugin check
opencode plugin update
```

Si `~/.config/opencode/opencode-mem.jsonc` n'existe pas, le toolkit crée une
configuration minimale. Le provider est déduit de `MODEL_MEDIUM`, puis
`MODEL_HIGH`/`MODEL_LOW`, et `opencodeModel` vaut `inherit`. Un fichier
existant n'est jamais écrasé.

Le premier usage du moteur d'embeddings local peut télécharger son modèle.

## Modèles

Le profil par défaut reste GitHub Copilot :

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

Les overrides persistants par agent restent dans `.env.local`.

## Commandes utiles

```bash
just install
just profile copilot
just config
just doctor
just plugins
just test
just uninstall
```

Depuis un autre dépôt, utilise directement `oc` afin de conserver ce dépôt
comme workspace.

## Codex

La synchronisation Codex reste indépendante du runtime OpenCode :

```bash
oc sync codex --dry-run
oc sync codex
oc codex install
oc codex doctor
```

Les protections contre l'écrasement des fichiers utilisateur restent en place.

## Migration depuis l'ancienne installation

`just install` réalise la migration npm et retire le lien toolkit `oc2`.
Les anciens conteneurs ou volumes Docker ne sont pas supprimés automatiquement.

Pour vérifier qu'il ne reste pas d'ancien CLI npm :

```bash
npm list -g --depth=0 | grep -i opencode
command -v opencode
command -v opencode2 || true
opencode --version
```

Après migration, le chemin supporté par le toolkit est uniquement `oc`.

## Contribuer

Toute modification du toolkit passe par une PR et les checks pertinents doivent
être verts avant merge. Voir [docs/fr/CONTRIBUTING.md](docs/fr/CONTRIBUTING.md).
