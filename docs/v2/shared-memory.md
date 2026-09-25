# V2 — Mémoire partagée multi-machine

## État

**Implémenté.**

La V2 utilise `harness-memory` comme stockage actif. Une nouvelle installation de `main` démarre avec un backend SQLite local propre ; aucune donnée V1 n'est migrée.

```text
OAT_MEMORY_BACKEND=local      # défaut V2
OAT_MEMORY_BACKEND=postgres   # mémoire partagée
OAT_MEMORY_BACKEND=legacy     # compatibilité explicite V1 uniquement
```

La branche `v1` conserve l'ancienne architecture Git/Markdown.

## Architecture

```text
OpenCode 2
   │
   ├── opencode-memory-plugin
   │      └── session idle / completed
   │             └── extraction durable existante
   │
   ├── contexte borné au lancement
   │
   └── oat-memory MCP
          │
          ▼
   toolkit memory bridge
          │
          ├── local    → SQLite harness-memory
          └── postgres → PostgreSQL harness-memory
```

Le toolkit ne dépend pas de la structure physique interne de PostgreSQL. Son contrat est :

```text
backend + namespace stable
```

`harness-memory` reste propriétaire de ses tables et migrations.

## Namespaces

Les namespaces sont calculés par le toolkit et restent identiques entre deux clones du même dépôt :

```text
oat:project:ylascaux/opencode-agent-toolkit
oat:project:ylascaux/livalyo-website
oat:user:default
```

Résolution du projet :

1. `OAT_MEMORY_PROJECT` si explicitement défini ;
2. remote Git canonique `owner/repo` ;
3. nom local du dépôt en dernier recours.

Le chemin absolu local n'entre jamais dans l'identité durable.

Les faits/architectures/décisions/conventions/issues sont stockés dans le namespace projet. Les préférences `workstyle` et `hat_preference` sont stockées dans `oat:user:default` et deviennent donc communes aux projets et aux machines.

## Capture automatique

Le plugin existant reste l'extracteur. La logique de capture déjà qualifiée n'a pas été réécrite :

```text
session terminée / idle
       ↓
messages user + assistant
       ↓
extracteur
       ↓
handoff + candidats durables
```

En `local` ou `postgres`, le plugin n'utilise plus :

- le vault Git ;
- `git pull` / `git commit` / `git push` ;
- la queue locale accept/promote ;
- la double écriture.

Il envoie directement le handoff et les souvenirs valides au bridge V2. La déduplication exacte est faite avant `create_atom`.

En `legacy`, l'ancien comportement reste disponible explicitement.

## Lecture

Au lancement de `oc`, le contexte durable est rendu par le bridge V2 et injecté dans OpenCode avec une taille bornée.

Le MCP `oat-memory` expose :

- `memory_status`
- `memory_search`
- `memory_render`
- `memory_propose`

Le backend PostgreSQL n'est jamais copié dans la configuration générée. Le DSN reste une variable d'environnement locale.

## Installation locale

`just install` prépare automatiquement un environnement Python isolé sous :

```text
~/.local/share/opencode-agent-toolkit/python-v2/
```

Il contient `harness-memory` et le driver PostgreSQL. Aucun `pip install` global n'est nécessaire.

Dans l'image runtime du toolkit, les dépendances sont déjà présentes et le Python du conteneur est réutilisé.

## Passer à PostgreSQL

Sur le premier PC :

```bash
git pull
just install
oc memory configure-postgres 'postgresql://USER:PASSWORD@HOST:5432/DB'
oc memory status
```

La commande :

1. prépare le runtime Python V2 ;
2. ouvre réellement `harness-memory` sur le DSN ;
3. vérifie la connexion et initialise le stockage si nécessaire ;
4. **n'écrit `.env.local` qu'après validation réussie**.

Le DSN n'est pas imprimé.

Sur le second PC :

```bash
git pull
just install
oc memory configure-postgres 'postgresql://USER:PASSWORD@HOST:5432/DB'
oc memory status
```

Avec le même remote Git du projet, les deux machines utilisent automatiquement le même namespace.

```text
MacBook A ─┐
           ├── PostgreSQL ── oat:project:owner/repo
MacBook B ─┘               └─ oat:user:default
```

Aucune synchronisation Git n'est nécessaire.

## Backend local

Pour revenir à un stockage V2 local :

```bash
oc memory configure-local
oc memory status
```

Le fichier par défaut est :

```text
~/.local/share/opencode-agent-toolkit/memory-v2.sqlite
```

Il peut être surchargé par `OAT_MEMORY_LOCAL_PATH`.

## Commandes V2

```bash
oc memory status
oc memory namespace
oc memory show
oc memory add decision "Titre" "Information durable"
oc memory capture-on
oc memory capture-off
```

Les anciennes commandes liées au cycle Git (`candidates`, `accept`, `promote`, `push`, `sync`) répondent explicitement qu'elles ne s'appliquent pas au backend V2.

## Résilience

La mémoire est auxiliaire au coding :

- un échec de rendu mémoire ne doit pas empêcher OpenCode de démarrer ;
- les erreurs de capture restent traçables et la queue de capture peut être reprise ;
- aucune boucle de reconnexion agressive n'est lancée ;
- `just doctor` teste le backend actif.

`oc memory configure-postgres` est volontairement plus strict : il refuse la configuration si le backend n'est pas joignable.

## Sécurité

- `.env.local` est écrit avec des permissions privées quand la plateforme le permet.
- Le DSN PostgreSQL n'est jamais sérialisé dans `OPENCODE_CONFIG_CONTENT`.
- Les enfants ACP ne reçoivent ni le DSN, ni `oat-memory`, ni la capture automatique.
- Les résultats mémoire sont bornés avant injection dans le contexte.
- Le plugin conserve ses filtres de secrets avant extraction/persistance.

## Checkpoints

Les checkpoints de conversation OpenCode restent locaux.

La V2 partage uniquement la mémoire durable. Cela évite de coupler deux processus OpenCode à un même état de conversation tant qu'un besoin réel n'est pas démontré.

## Sauvegarde

Le backend PostgreSQL doit être sauvegardé avec les outils PostgreSQL habituels. Git n'est plus le mécanisme de sauvegarde du stockage actif V2.

Le backend SQLite local peut être sauvegardé comme un fichier lorsque le processus est arrêté ou via une méthode SQLite cohérente.

## V1 → V2

**Aucune migration.**

Le stockage V2 commence vide. L'ancien vault n'est ni importé ni double-écrit. La branche `v1` reste disponible si l'ancien contenu doit être consulté.

## Références Octop

L'implémentation s'inspire des choix de séparation backend/namespace d'Octop, sans embarquer Octop lui-même :

- https://github.com/TencentCloud/Octop/blob/main/src/octop/infra/agents/memory_backend.py
- https://github.com/TencentCloud/Octop/blob/main/src/octop/api/routers/memory_portable.py
- https://github.com/TencentCloud/Octop/blob/main/docs/adr/002-database-backends.md
