# Mémoire long terme basée sur Git

Le toolkit peut injecter une petite mémoire long terme, contrôlée par l'utilisateur, dans les prompts générés des agents. La lecture est **désactivée par défaut** et fonctionne avec OpenCode V1 comme V2. La capture automatique de candidats est séparée, également désactivée par défaut, et cible OpenCode V2.

## Conception

Le dépôt mémoire privé reste du Markdown/JSON lisible :

```text
projects/   contexte, décisions et conventions propres à un projet
workstyle/  préférences de travail transverses
hats/       casquettes réutilisables associées aux agents
inbox/      candidats acceptés/promus ; jamais injecté directement
```

Les agents reçoivent uniquement du texte rendu. Le clone Git privé n'est pas monté dans la sandbox et le runtime agent n'a pas de droit d'écriture direct dessus.

La mémoire ne peut pas accorder de permissions, contourner l'approbation d'un plan, affaiblir la sandbox ou remplacer des instructions explicites du dépôt/de l'utilisateur.

## Activation de la lecture

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

Désactivation et synchronisation :

```bash
just memory-off
just memory-sync
```

`memory-on` enregistre l'activation et éventuellement l'URL du dépôt dans `.env.local`.

## Détection du projet

Le toolkit détecte la racine Git courante et le remote `origin`. `projects/index.json` associe noms/remotes à un identifiant mémoire stable. Si aucune association ne correspond, `projects/<nom-de-la-racine-git>/` est utilisé lorsqu'il existe. `OAT_MEMORY_PROJECT` permet de forcer un identifiant.

Seuls les fichiers Markdown à la racine du projet correspondant sont injectés. `sessions/` et `inbox/` sont exclus du contexte automatique.

## Casquettes

`hats/assignments.json` associe les agents à des casquettes stockées dans `hats/<nom>.md`. Une casquette décrit des priorités et habitudes de travail ; elle ne remplace ni le rôle technique ni la carte de permissions de l'agent.

`OAT_MEMORY_EXTRA_HATS=foo,bar` ajoute temporairement des casquettes aux agents déjà mappés.

## Capture automatique de candidats (V2)

Activez-la uniquement après la mémoire :

```bash
just memory-capture-on
```

Le plugin V2 écoute le nouvel événement `session.status` lorsque son état devient `idle`, ainsi que l'ancien `session.idle` encore présent pour compatibilité. Les deux chemins sont dédupliqués par hash de conversation.

À la fin d'une session, le plugin :

1. lit uniquement le texte utilisateur/assistant ;
2. ignore les sorties d'outils, commandes shell et raisonnements internes ;
3. limite l'entrée de l'extracteur ;
4. demande au modèle d'extraction uniquement des faits/préférences durables ;
5. rejette déterministement plusieurs formes courantes de secrets ;
6. stocke uniquement des candidats structurés, jamais la transcription brute.

Les candidats locaux vivent par défaut dans :

```text
${XDG_STATE_HOME:-$HOME/.local/state}/opencode-agent-toolkit/memory/
├── candidates/
├── accepted/
├── rejected/
└── promoted/
```

Le modèle d'extraction utilise `OAT_MEMORY_EXTRACTOR_MODEL`, puis `MODEL_LOW` par défaut. La capture est volontairement fail-open sauf avec `OAT_MEMORY_CAPTURE_STRICT=1` : une panne de l'extracteur ne doit pas casser une session de développement.

Paramètres principaux :

```bash
OAT_MEMORY_CAPTURE_ENABLED=0
OAT_MEMORY_CAPTURE_STRICT=0
OAT_MEMORY_CAPTURE_MAX_INPUT_CHARS=18000
OAT_MEMORY_MAX_CANDIDATES_PER_SESSION=5
# OAT_MEMORY_EXTRACTOR_MODEL=github-copilot/gpt-5.6-luna
```

Un candidat identique observé plusieurs fois n'est pas dupliqué : son compteur `occurrences` et `last_seen_at` sont mis à jour tant qu'il reste en attente.

Pour V1, ou sans capture automatique, un candidat peut être créé manuellement :

```bash
just memory-add decision "Titre" "Décision durable" --target project/decisions.md
```

## Revue et cycle de confiance

Lister et inspecter :

```bash
just memory-candidates
just memory-candidate abcdef123456
```

Rejeter ne touche jamais Git :

```bash
just memory-reject abcdef123456
```

Accepter est une action utilisateur explicite. Elle crée un fichier sous `inbox/accepted/` et un commit **local** dans le dépôt mémoire. `inbox/` reste hors du contexte injecté :

```bash
just memory-accept abcdef123456
```

Pour pousser le commit immédiatement :

```bash
just memory-accept abcdef123456 push=true
```

La promotion est une seconde action explicite. Elle ajoute le fait dans un fichier réellement injecté (`projects/`, `workstyle/` ou `hats/`) et déplace la note de provenance vers `inbox/promoted/` :

```bash
just memory-promote abcdef123456
# ou cible explicite
just memory-promote abcdef123456 project/decisions.md push=true
```

Cibles autorisées : `project/context.md`, `project/decisions.md`, `project/conventions.md`, `project/known-issues.md`, `project/current.md`, les quatre fichiers `workstyle/*.md` standards, ou `hat:<nom>`.

Pour publier des commits locaux déjà créés :

```bash
just memory-push
```

Les commandes d'acceptation/promotion refusent de travailler si le clone mémoire contient déjà des changements non commités. Elles utilisent `git pull --ff-only` et ne forcent jamais un historique divergent.

## Synchronisation et limite de contexte

```bash
OAT_MEMORY_ENABLED=0
OAT_MEMORY_REPO=git@github.com:USER/opencode-memory.git
OAT_MEMORY_AUTO_SYNC=1
OAT_MEMORY_SYNC_INTERVAL_SECONDS=300
OAT_MEMORY_MAX_CHARS=12000
OAT_MEMORY_STRICT=0
```

Le `git pull` automatique est limité par un timestamp placé dans le `.git` du clone. En cas d'échec, le dernier snapshot local est utilisé avec un avertissement, sauf si `OAT_MEMORY_STRICT=1`.

Le contexte rendu est borné. Par défaut, environ 75 % du budget est réservé au projet/workstyle et 25 % aux casquettes.

## Modèle de sécurité

```text
conversation OpenCode V2
        │
        ▼
 extracteur conservateur
        │
        ▼
candidat local (non Git)
   │             │
 reject          accept explicite
   │             │
   ▼             ▼
local/rejected   Git inbox/accepted
                      │
               promote explicite
                      │
                      ▼
             projects/workstyle/hats
```

Aucun événement de session ne commit ou ne push automatiquement le dépôt mémoire. La capture peut produire un candidat ; seule une commande utilisateur peut le faire entrer dans Git, puis une seconde commande peut le rendre actif dans la mémoire injectée.

Comme le stockage reste du Markdown standard, le dépôt peut être ouvert directement comme vault Obsidian.
