# OpenCode Agent Toolkit

Toolkit multi-agents **multi-runtime** pour OpenCode V1/V2 et Codex. Une même source canonique décrit les agents et les skills ; les adapters runtime génèrent ensuite les artefacts propres à OpenCode ou Codex sans dupliquer les prompts ni les politiques.

Le plan de contrôle reste volontairement court et auditable :

```text
meta-router -> lead/orchestrator -> specialist
```

Les garde-fous de permissions, de fiabilité, d'isolation Docker/DinD et de mémoire restent indépendants du runtime.

## État du projet

La première release multi-runtime est préparée comme **v0.1.0**. Le socle local couvre :

- agents canoniques dans `agents/<name>/` ;
- skills portables dans `skills/<name>/` ;
- OpenCode V1/V2 ;
- génération et lifecycle local Codex ;
- mémoire Git privée optionnelle via MCP ;
- sandbox et DinD isolés ;
- acceptance runtime depuis un projet externe jetable.

`VERSION` est la source de vérité pour les releases et `CHANGELOG.md` décrit les changements publiés.

## Démarrer en cinq minutes

Prérequis : Git, Bash, Python 3, Node.js, Docker, OpenCode et [`just`](https://github.com/casey/just). Sur macOS : `brew install just`.

```bash
git clone https://github.com/ylascaux/opencode-agent-toolkit.git
cd opencode-agent-toolkit
just install
just install-user
just install-oc2
just models
just doctor
```

`just install` crée `.env` s'il est absent, prépare l'environnement local, génère les configurations OpenCode et exécute les tests Python. Pour la validation complète du dépôt :

```bash
just check
```

## OpenCode

Après installation des lanceurs, travaillez depuis le dépôt cible :

```bash
cd ~/Projects/mon-projet
oc .
```

Pour OpenCode V2 :

```bash
oc2 .
```

Les configurations générées du toolkit restent `opencode.jsonc` et `opencode.v2.jsonc`. Le launcher conserve le répertoire courant du projet et ajoute les skills toolkit sans masquer les skills locaux du projet.

## Codex local

Le même graphe normalisé d'agents et de skills alimente Codex :

```bash
cd /chemin/vers/opencode-agent-toolkit
oc sync codex

cd ~/Projects/mon-projet
oc codex install
oc codex doctor
```

Pour enregistrer également la mémoire MCP portable :

```bash
oc codex install --with-memory
```

Pour retirer uniquement les fichiers gérés par le toolkit :

```bash
oc codex uninstall
```

Le lifecycle Codex protège les fichiers utilisateur : un agent ou skill préexistant, ou un fichier géré modifié manuellement, provoque un conflit au lieu d'être écrasé ou supprimé silencieusement.

## Agents et skills portables

Source canonique :

```text
agents/<name>/
  agent.json
  prompt.md
  permissions.json

skills/<name>/
  skill.json
  SKILL.md
```

Synchronisation runtime :

```bash
oc sync opencode
oc sync codex
oc sync all

oc sync codex --dry-run
oc sync codex --check
```

`sync` génère des artefacts jetables et déterministes. Il ne publie aucune ressource distante et ne change pas implicitement l'agent racine.

## Mémoire Git privée optionnelle

La mémoire est fournie par le plugin autonome `ylascaux/opencode-memory-plugin`. Le toolkit le configure/consomme mais ne duplique pas son moteur.

```bash
cd ~/Projects/mon-projet
oc memory enable git@github.com:USER/opencode-memory.git
oc memory status
oc memory capture-on
oc memory candidates
```

Pour Codex, le MCP portable expose uniquement les opérations non destructives/portables : status, search, render, propose et candidates. Les opérations `accept`, `promote` et `push` restent explicitement humaines.

Le clone mémoire privé n'est pas monté directement dans la sandbox ou exposé à Codex.

Voir [la documentation mémoire](docs/fr/MEMORY.md).

## Isolation et sécurité

Le runtime Docker est le chemin principal. Le toolkit conserve les invariants suivants :

- pas de montage du `docker.sock` hôte dans le runtime normal ;
- DinD dédié pour les serveurs persistants ;
- rootless DinD pour les tâches managées ;
- frontières de permissions par agent ;
- pas de secrets dans les artefacts générés ;
- aucune promotion/push automatique de mémoire ;
- installation/uninstall Codex basée sur un manifest d'ownership et des hashes.

Diagnostics utiles :

```bash
just doctor
just sandbox-doctor
oc codex doctor
```

## Acceptance runtime

L'acceptance intégrée utilise une copie temporaire du toolkit et un dépôt Git externe synthétique. Elle n'utilise pas le HOME/XDG réel, `.env.local`, les credentials provider ou un vault mémoire privé.

```bash
OAT_ACCEPTANCE_SKIP_MEMORY=1 python3 -B scripts/runtime-acceptance
```

La CI exécute aussi un smoke Docker contre un vrai serveur OpenCode V2 authentifié. L'intégration du plugin mémoire privé utilise le vrai repo piné lorsqu'un token inter-repo dédié est configuré ; sinon le skip est explicite et aucun faux serveur MCP n'est substitué.

Voir [Runtime acceptance](docs/en/RUNTIME_ACCEPTANCE.md).

## Repères développeur

```bash
just config                  # régénère les configurations OpenCode
just check                   # génération + tests Python + tests runtime Node
just agents                  # inspecte les agents et leur topologie
just new-agent mon-agent --parent orchestrator
just reliability             # politique de fiabilité effective
just configure-litellm       # découverte LiteLLM optionnelle
```

Les overrides persistants par agent doivent aller dans `.env.local` afin de ne pas être écrasés par `just profile`.

## Release

Valider les métadonnées uniquement :

```bash
python3 -B scripts/release-check --metadata-only --tag "v$(cat VERSION)"
```

Valider l'ensemble des gates locales de release :

```bash
python3 -B scripts/release-check
```

La release doit être mergée sur `main` **avant** de créer le tag annoté correspondant. Voir [le processus de release](docs/fr/RELEASE.md) et le [changelog](CHANGELOG.md).

## Documentation

- [Documentation française](docs/fr/README.md)
- [Documentation anglaise](docs/en/README.md)
- [Architecture multi-runtime](docs/fr/MULTI_RUNTIME.md)
- [Adapter Codex](docs/fr/CODEX_ADAPTER.md)
- [Workflow cross-runtime](docs/fr/CROSS_RUNTIME_WORKFLOW.md)
- [Architecture système](docs/fr/SYSTEM_ARCHITECTURE.md)
- [Permissions](docs/fr/PERMISSIONS.md)
- [Fiabilité](docs/fr/RELIABILITY.md)
- [Sandbox](docs/fr/SANDBOX.md)
- [Processus de release](docs/fr/RELEASE.md)

Les contrats machine lisibles sont dans [`contracts/`](contracts/), notamment `agent-handoff.schema.json` et `routing-decision.schema.json`.
