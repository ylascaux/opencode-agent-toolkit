# Mémoire long terme basée sur Git

Le toolkit peut injecter une petite mémoire long terme, contrôlée par l'utilisateur, dans les prompts générés des agents. La fonctionnalité est **désactivée par défaut** et fonctionne avec OpenCode V1 comme V2 : la mémoire est rendue avant l'application des politiques de fiabilité.

## Conception

Le dépôt mémoire est un dépôt privé Markdown/JSON organisé en quatre périmètres :

```text
projects/   contexte, décisions et conventions propres à un projet
workstyle/  préférences de travail transverses
hats/       casquettes réutilisables associées aux agents
inbox/      futurs candidats ; jamais injectés par défaut
```

Les agents reçoivent uniquement du texte rendu. Ils n'obtiennent aucun accès direct en écriture au filesystem ou au Git du dépôt mémoire.

La mémoire ne peut pas accorder de permissions, contourner l'approbation d'un plan, affaiblir la sandbox ou remplacer des instructions explicites du dépôt/de l'utilisateur.

## Activation

Après `just install` :

```bash
just memory-on git@github.com:USER/opencode-memory.git
just memory-status
just memory-show orchestrator
```

Le dépôt est cloné par défaut dans :

```text
${XDG_DATA_HOME:-$HOME/.local/share}/opencode-agent-toolkit/memory
```

Désactivation :

```bash
just memory-off
```

Synchronisation forcée :

```bash
just memory-sync
```

`memory-on` enregistre l'activation et éventuellement l'URL du dépôt dans `.env.local`, donc un changement de profil de modèles ne les écrase pas.

## Détection du projet

Le toolkit détecte la racine Git courante et le remote `origin`. `projects/index.json` permet d'associer des noms/remotes à un identifiant mémoire stable :

```json
{
  "version": 1,
  "projects": [
    {
      "id": "opencode-agent-toolkit",
      "match": {
        "names": ["opencode-agent-toolkit"],
        "remotes": ["ylascaux/opencode-agent-toolkit"]
      }
    }
  ]
}
```

Si aucune association explicite ne correspond, `projects/<nom-de-la-racine-git>/` est utilisé lorsqu'il existe. `OAT_MEMORY_PROJECT` permet de forcer un identifiant.

Seuls les fichiers Markdown à la racine du projet correspondant sont injectés. `sessions/` et `inbox/` sont volontairement exclus du contexte automatique.

## Casquettes

`hats/assignments.json` associe un agent à une ou plusieurs casquettes :

```json
{
  "version": 1,
  "default": [],
  "agents": {
    "orchestrator": ["architect", "software-engineer"],
    "platform-architect": ["architect", "platform-engineer"]
  }
}
```

Une casquette est stockée dans `hats/<nom>.md`. Elle décrit des priorités et habitudes de travail ; elle ne remplace ni le rôle technique de l'agent ni sa carte de permissions.

`OAT_MEMORY_EXTRA_HATS=foo,bar` permet d'ajouter temporairement des casquettes à tous les agents déjà mappés.

## Synchronisation et limite de contexte

Paramètres principaux :

```bash
OAT_MEMORY_ENABLED=0
OAT_MEMORY_REPO=git@github.com:USER/opencode-memory.git
OAT_MEMORY_AUTO_SYNC=1
OAT_MEMORY_SYNC_INTERVAL_SECONDS=300
OAT_MEMORY_MAX_CHARS=12000
OAT_MEMORY_STRICT=0
```

Le `git pull` automatique est limité par un timestamp placé dans le `.git` du clone. En cas d'échec, le dernier snapshot local est utilisé avec un avertissement, sauf si `OAT_MEMORY_STRICT=1`.

Le contexte rendu est borné. Par défaut, environ 75 % du budget de caractères est réservé au projet/workstyle et 25 % aux casquettes.

## Sandbox

La mémoire est préparée sur l'hôte de confiance avant le démarrage d'OpenCode. Le clone privé **n'est pas monté dans la sandbox d'exécution**. Les agents sandboxés ne voient que le texte déjà injecté dans leur prompt généré.

## Politique d'écriture de la phase 1

La phase 1 est volontairement en lecture seule côté runtime agent. L'extraction automatique des conversations, le score de confiance, la consolidation et les commits Git devront être ajoutés ensuite dans un pipeline contrôlé séparé. Cela évite qu'une conversation isolée ou qu'un projet compromis réécrive silencieusement une mémoire personnelle durable.

Comme le stockage reste du Markdown standard, le dépôt pourra ensuite être ouvert directement comme vault Obsidian sans migration.
