# V2 — Mémoire partagée multi-machine

## But

La mémoire V2 doit être utilisable depuis plusieurs machines sans dépendre d'une synchronisation Git du stockage actif.

Cible :

```text
MacBook travail ─┐
                 │
MacBook perso ───┼──► PostgreSQL partagé
                 │        │
serveur ─────────┘        └── mémoire harness
```

Chaque machine exécute `oc` localement. Le stockage durable de la mémoire est partagé.

## Ce que nous reprenons d'Octop

Octop sépare clairement :

1. le control plane ;
2. les checkpoints de conversation ;
3. la mémoire de l'agent ;
4. les fichiers de workspace.

Le toolkit V2 ne reprend que la partie utile : **backend mémoire PostgreSQL + namespace explicite**.

Dans Octop, le résolveur mémoire accepte notamment :

```json
{
  "memory": {
    "backend": {
      "type": "postgres",
      "dsn": "postgresql://..."
    }
  }
}
```

Référence :
https://github.com/TencentCloud/Octop/blob/main/src/octop/infra/agents/memory_backend.py

## Point important : namespace, pas hypothèse de schéma par agent

Certaines documentations Octop historiques parlent de schémas PostgreSQL par agent. Le code actuel de la route de portabilité précise cependant que la mémoire PostgreSQL utilise des tables partagées dans le schéma `harness_memory`, avec isolation par colonne `namespace`.

Référence :
https://github.com/TencentCloud/Octop/blob/main/src/octop/api/routers/memory_portable.py

La V2 doit donc considérer comme contrat :

```text
DSN partagé
  └── namespace mémoire stable
```

et **ne jamais dépendre d'une structure physique interne** telle que `agent_<id>` ou d'un schéma PostgreSQL spécifique.

## Identité mémoire proposée

Le namespace doit être stable entre les machines.

Proposition :

```text
oat:<scope>:<identifier>
```

Exemples :

```text
oat:user:default
oat:project:ylascaux/opencode-agent-toolkit
oat:project:ylascaux/livalyo-website
```

Les identifiants projet doivent être dérivés d'une identité stable du dépôt, idéalement :

1. remote Git canonique `owner/repo` ;
2. fallback sur un identifiant explicitement configuré ;
3. dernier fallback sur un slug local.

Le chemin absolu local ne doit jamais faire partie de l'identité durable.

## Modèle de mémoire V2

La mémoire doit rester structurée conceptuellement comme aujourd'hui, mais le stockage actif n'est plus un vault Git.

Scopes proposés :

- `project` : architecture, décisions, état durable du projet ;
- `workstyle` : préférences de travail réutilisables ;
- `lessons` : enseignements transverses validés ;
- `session` : uniquement pour le contexte temporaire si nécessaire.

Les agents doivent récupérer uniquement le contexte pertinent pour la tâche courante.

## Multi-machine

Deux machines peuvent pointer vers le même DSN et le même namespace.

```text
Machine A
  └── memory backend ─┐
                      ├── PostgreSQL
Machine B             │      └── namespace identique
  └── memory backend ─┘
```

Octop recommande explicitement, pour sa mémoire PostgreSQL, de partager le même DSN et le même namespace plutôt que de déplacer un fichier SQLite entre hôtes.

Référence :
https://github.com/TencentCloud/Octop/blob/main/src/octop/api/routers/memory_portable.py

## Concurrence : règle de sécurité V2

Le fait que PostgreSQL accepte plusieurs connexions ne suffit pas à garantir que deux instances du plugin puissent écrire simultanément sans conflit logique.

Avant d'activer le mode multi-writer par défaut, il faudra vérifier expérimentalement :

- deux écritures concurrentes sur le même namespace ;
- mise à jour concurrente d'un même souvenir ;
- déduplication concurrente ;
- transaction interrompue ;
- reprise après perte réseau ;
- idempotence des écritures ;
- comportement des checkpoints si nous les partageons aussi.

Tant que ces tests ne sont pas verts, le mode supporté est :

```text
multi-reader + single logical writer
```

ou une sérialisation applicative légère.

## Checkpoints

La mémoire durable et les checkpoints de conversation doivent rester des responsabilités séparées.

V2 phase 1 :

- mémoire durable : PostgreSQL partagé ;
- sessions/checkpoints OpenCode : locaux, sauf besoin démontré.

On ne partagera les checkpoints entre machines que si cela apporte un bénéfice réel et si le runtime OpenCode le permet proprement.

## Configuration

Variables proposées :

```bash
OAT_MEMORY_BACKEND=postgres
OAT_MEMORY_POSTGRES_DSN="postgresql://..."
OAT_MEMORY_NAMESPACE_PREFIX="oat"
OAT_MEMORY_SHARED=1
```

Fallback :

```bash
OAT_MEMORY_BACKEND=local
```

Les secrets ne doivent jamais être écrits dans la configuration générée en clair si un mécanisme d'environnement est disponible.

## Résilience

Le plugin mémoire ne doit pas empêcher OpenCode de démarrer si PostgreSQL est indisponible.

Comportement attendu :

1. tentative de connexion bornée ;
2. si échec : diagnostic clair ;
3. bascule en lecture de contexte local minimal ou mémoire désactivée ;
4. aucune boucle de retry agressive ;
5. reprise au prochain lancement ou au prochain accès mémoire.

Une indisponibilité mémoire ne doit pas casser les fonctions de coding de base.

## Sauvegarde

Le stockage actif PostgreSQL doit être sauvegardé comme une base, pas synchronisé par Git.

Minimum :

- backup PostgreSQL régulier ;
- test de restauration ;
- rétention simple ;
- aucune dépendance au backup pour le fonctionnement quotidien.

Un export Markdown peut être ajouté plus tard pour audit humain, mais ce n'est pas un mécanisme de synchronisation.

## V1 → V2

**Pas de migration.**

Le contenu actuel de la mémoire V1 ne justifie pas la complexité d'un import.

La branche `v1` conserve le système actuel si une consultation ponctuelle est nécessaire. La V2 crée une mémoire vide lors de son premier démarrage.

## Hors périmètre

La V2 mémoire n'inclut pas :

- Octop Server ;
- FastAPI ;
- dashboard React ;
- gestion multi-utilisateur Octop ;
- stockage S3 des workspaces ;
- messageries IM ;
- cron Octop ;
- RAG documentaire Octop.

Le but reste une intégration fine dans le toolkit OpenCode.
