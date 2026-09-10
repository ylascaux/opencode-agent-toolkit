# Mémoire Git externe

`opencode-agent-toolkit` ne contient plus l'implémentation de la mémoire. Elle est fournie par le dépôt autonome **`ylascaux/opencode-memory-plugin`**, tandis que les données durables personnelles/projet restent dans un dépôt Git privé séparé comme `ylascaux/opencode-memory`.

```text
opencode-agent-toolkit
        │ configure / consomme
        ▼
opencode-memory-plugin
        │ lit / consolide
        ▼
dépôt privé opencode-memory
```

On sépare ainsi l'orchestration des agents, l'adaptateur runtime OpenCode et les données privées, avec un versionnement indépendant.

## Interface utilisateur

Les commandes quotidiennes ne nécessitent pas d'être dans le dépôt du toolkit. Le wrapper global `oc` conserve le répertoire courant et expose la mémoire comme sous-commande :

```bash
cd ~/Projects/mon-projet
oc memory status
oc memory candidates
oc memory show orchestrator
```

Le plugin autonome expose également `oc-memory` lorsqu'il est installé globalement. `opencode-memory` reste un alias de compatibilité.

Les recettes `just memory-*` sont conservées comme raccourcis de développement/maintenance, mais ne constituent plus l'interface principale d'utilisation.

## Compatibilité

Le plugin expose un adaptateur OpenCode V1 et un adaptateur V2 autour du même cœur mémoire.

| Capacité | OpenCode V1 | OpenCode V2 bêta |
| --- | --- | --- |
| Capture automatique de candidats | oui | oui |
| Stockage projet/workstyle/hats | oui | oui |
| Cycle review/accept/promote | oui | oui |
| Injection native par hook plugin | oui | pas encore exposée par l'API V2 |
| Injection via le toolkit | inutile | oui |

En V1, le plugin utilise directement `experimental.chat.system.transform`. En V2, OpenCode n'expose actuellement aucun hook équivalent ; le toolkit appelle donc le renderer stable du plugin lors de la génération des prompts V2. Toute la logique mémoire reste néanmoins dans le dépôt externe.

## Activation

Après l'installation initiale du toolkit :

```bash
oc memory enable git@github.com:USER/opencode-memory.git
oc memory status
```

Le plugin externe est cloné automatiquement depuis `git@github.com:ylascaux/opencode-memory-plugin.git` vers :

```text
${XDG_DATA_HOME:-$HOME/.local/share}/opencode-agent-toolkit/plugins/opencode-memory-plugin
```

Le ref de bootstrap est `main`. Dès qu'une release est taguée, il est préférable de la pinner :

```bash
OAT_MEMORY_PLUGIN_REF=v0.1.0
```

Cela rend les exécutions du toolkit reproductibles.

## Capture automatique

La capture est indépendante de la lecture mémoire et reste désactivée par défaut :

```bash
oc memory capture-on
```

V1 et V2 extraient uniquement un texte borné provenant des messages utilisateur/assistant. Le reasoning, les sorties shell et les résultats d'outils ne sont pas persistés. Les observations extraites arrivent uniquement dans la quarantaine locale des candidats.

```text
session
  │
  ▼
candidat local
  │ validation humaine explicite
  ▼
inbox/accepted        # toujours inactif
  │ promotion humaine explicite
  ▼
projects/workstyle/hats
  │ push explicite
  ▼
remote Git privé
```

Un événement de session ne committe et ne pousse jamais le dépôt mémoire privé.

## Cycle des candidats

```bash
oc memory candidates
oc memory candidate a31f92d780cc
oc memory reject a31f92d780cc
oc memory accept a31f92d780cc
oc memory promote a31f92d780cc
oc memory push
```

Forcer une cible de promotion si nécessaire :

```bash
oc memory promote a31f92d780cc --target workstyle/preferences.md
```

`--push` reste disponible sur `accept` et `promote`, mais le push séparé reste le comportement par défaut le plus sûr.

## Candidat manuel

```bash
oc memory add workstyle \
  'Prefer Just' \
  'Prefer Justfiles over Makefiles for project automation.' \
  --target workstyle/preferences.md
```

## Contexte rendu

Afficher exactement ce que reçoit un agent :

```bash
oc memory show orchestrator
```

Le plugin externe détecte le dépôt Git courant, le mappe via `projects/index.json`, charge la mémoire projet, le workstyle transversal et les hats de l'agent, puis borne le contexte avec `OAT_MEMORY_MAX_CHARS`.

## CLI autonome

Pour utiliser le plugin sans toolkit, le package fournit un vrai CLI global :

```bash
oc-memory status
oc-memory sync
oc-memory candidates
oc-memory show <id>
oc-memory accept <id>
oc-memory promote <id>
oc-memory push
```

Le CLI fonctionne depuis n'importe quel répertoire et utilise le dépôt Git courant pour déterminer le scope projet.

## Configuration

Intégration toolkit/plugin :

```bash
OAT_MEMORY_PLUGIN_REPO=git@github.com:ylascaux/opencode-memory-plugin.git
OAT_MEMORY_PLUGIN_REF=main
OAT_MEMORY_PLUGIN_AUTO_SYNC=1
OAT_MEMORY_PLUGIN_SYNC_INTERVAL_SECONDS=300
```

Vault privé :

```bash
OAT_MEMORY_ENABLED=0
OAT_MEMORY_REPO=git@github.com:USER/opencode-memory.git
OAT_MEMORY_AUTO_SYNC=1
OAT_MEMORY_SYNC_INTERVAL_SECONDS=300
OAT_MEMORY_MAX_CHARS=12000
OAT_MEMORY_STRICT=0
```

Capture :

```bash
OAT_MEMORY_CAPTURE_ENABLED=0
OAT_MEMORY_CAPTURE_MAX_INPUT_CHARS=18000
OAT_MEMORY_MAX_CANDIDATES_PER_SESSION=5
# OAT_MEMORY_EXTRACTOR_MODEL=provider/model
```

Le plugin autonome accepte aussi les variables canoniques `OPENCODE_MEMORY_*`. Les alias `OAT_MEMORY_*` sont conservés pour rendre la migration du toolkit rétrocompatible, y compris le vault existant par défaut dans `~/.local/share/opencode-agent-toolkit/memory`.

## Gestion des échecs

Les opérations Git du plugin et du vault sont non interactives. Les mises à jour automatiques utilisent `fetch`, puis `pull --ff-only` ou checkout détaché d'un tag/ref explicite. Un checkout local du plugin contenant des modifications n'est jamais écrasé automatiquement.

Le vault mémoire doit être propre avant `accept` ou `promote`. Les cibles de promotion sont allowlistées et ne peuvent pas sortir du vault. Un échec de push n'annule jamais un commit local déjà valide.

## Frontière sandbox

Le dépôt mémoire privé n'est pas monté dans la sandbox du toolkit. En V2, les agents ne voient que le texte rendu dans leurs prompts. En V1, la mémoire est injectée via le hook OpenCode, sans donner d'accès shell au vault.

## Frontière de responsabilité

Le toolkit ne doit plus réembarquer de logique d'extraction ou de stockage mémoire. Les évolutions de capture, scoring, curation Git, retrieval ou futur support des context sources V2 appartiennent à `opencode-memory-plugin`. Ce dépôt ne conserve que l'installation/configuration et le bridge temporaire de rendu V2.
