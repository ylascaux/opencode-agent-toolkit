# V2 — Plan d'implémentation de la mémoire partagée

## Phase 0 — Validation technique

Avant de modifier le runtime quotidien :

- identifier précisément l'API publique de `harness-memory` utilisée par Octop ;
- pinner une version compatible ;
- valider PostgreSQL sur un environnement de test ;
- confirmer la sémantique exacte du namespace ;
- tester les lectures et écritures concurrentes ;
- mesurer le comportement en coupure réseau.

Critère de sortie : aucun détail de stockage interne Octop n'est nécessaire à l'intégration.

## Phase 1 — Adapter mémoire minimal

Créer une abstraction interne très petite :

```text
MemoryBackend
  ├── read/retrieve
  ├── remember/upsert
  ├── health
  └── namespace
```

Backends :

```text
postgres   # cible V2
local      # fallback/dev
```

Ne pas recopier le control plane d'Octop.

## Phase 2 — Identité stable des projets

Définir une fonction unique :

```text
resolve_project_memory_id(repo) -> stable id
```

Priorité :

1. remote Git canonique ;
2. override explicite ;
3. slug fallback.

Tests obligatoires :

- deux clones du même repo sur deux chemins différents obtiennent le même id ;
- deux repos différents de même nom local n'entrent pas en collision ;
- changement de répertoire local sans changement de remote conserve l'identité.

## Phase 3 — Lecture du contexte

Au lancement ou au premier prompt :

1. déterminer le namespace ;
2. récupérer uniquement les souvenirs pertinents ;
3. injecter un contexte borné ;
4. tracer les ids/résultats utilisés sans exposer de secrets.

Le retrieval doit être lazy et limité. Pas de dump complet de la mémoire dans le contexte.

## Phase 4 — Capture

Réutiliser le principe actuel :

```text
session.idle
   ↓
extraction
   ↓
classification
   ↓
écriture durable
```

La capture doit être :

- idempotente ;
- bornée ;
- tolérante aux interruptions ;
- non bloquante pour la fermeture d'OpenCode ;
- indépendante du chemin local de la machine.

## Phase 5 — Multi-PC

Scénario de qualification :

```text
PC A ouvre repo X
PC B ouvre repo X
PC A écrit mémoire M1
PC B retrouve M1
PC B écrit M2
PC A retrouve M2
```

Puis test de collision :

```text
PC A et PC B écrivent en même temps sur repo X
```

Critère de sortie : aucune perte silencieuse ni corruption.

Si le backend ne garantit pas suffisamment la concurrence logique, ajouter un verrou léger ou une sérialisation par namespace.

## Phase 6 — Doctor

Étendre `just doctor` / `oc memory status` avec :

- backend actif ;
- DSN masqué ;
- namespace courant ;
- connectivité ;
- version/schema détecté ;
- dernière lecture réussie ;
- dernière écriture réussie ;
- mode concurrence supporté ;
- fallback actif ou non.

Aucun secret complet dans les logs.

## Phase 7 — Backup

Documenter une procédure simple :

- dump régulier de la base ;
- restauration sur instance de test ;
- rétention ;
- alerte si le dernier backup valide est trop ancien.

Ne pas créer un système de backup applicatif complexe si PostgreSQL fournit déjà les primitives nécessaires.

## Phase 8 — Retrait du stockage Git actif

Quand PostgreSQL est qualifié :

- le vault Git n'est plus nécessaire au runtime V2 ;
- les commandes V1 restent disponibles uniquement sur la branche `v1`;
- aucun import automatique n'est réalisé ;
- aucun mécanisme de double écriture Git + PostgreSQL n'est conservé.

Objectif : une seule source de vérité.

## Tests de validation finaux

- démarrage sans PostgreSQL ;
- démarrage avec PostgreSQL ;
- lecture depuis deux machines ;
- écriture depuis deux machines ;
- namespace par repo ;
- repo déplacé localement ;
- remote identique sur deux clones ;
- coupure réseau pendant lecture ;
- coupure réseau pendant écriture ;
- reprise après redémarrage ;
- secrets absents des logs ;
- `just doctor` explicite ;
- OpenCode reste utilisable si la mémoire est indisponible.

## Non-objectifs

- migrer les données V1 ;
- répliquer Octop ;
- ajouter une UI dédiée ;
- partager tous les états OpenCode entre machines dès la première phase ;
- ajouter un broker ou une queue tant qu'un besoin réel n'est pas démontré.
