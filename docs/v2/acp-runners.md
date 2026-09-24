# V2 — ACP runners

## Objectif

ACP (Agent Client Protocol) devient la frontière entre l'orchestrateur V2 et les runtimes de coding externes.

OpenCode reste le runtime principal et possède déjà un serveur ACP natif :

```bash
opencode acp
```

La V2 ne réimplémente pas le protocole côté OpenCode et n'ajoute pas d'adaptateur externe.

Référence OpenCode :
https://opencode.ai/v2/docs/cli/acp/

Référence Octop :
https://github.com/TencentCloud/Octop/blob/main/docs/acp.md

## Séparation des responsabilités

```text
orchestrator
    │
    ▼
ACP runner manager
    │
    ├── opencode  -> opencode acp
    ├── codex     -> futur runner
    └── autres    -> futurs runners
```

Le registre des runners décrit uniquement comment démarrer un processus ACP approuvé.

Il ne contient pas de logique métier d'orchestration.

## Fondation implémentée

Le registre est dans :

```text
config/acp-runners.json
```

Le premier runner est :

```text
opencode -> opencode acp
```

Commandes :

```bash
oc runner list
oc runner doctor
oc runner command opencode
oc runner exec opencode
```

`oc runner exec` remplace le processus courant par le runner ACP et réserve stdout au protocole stdio.

`OPENCODE_BIN` reste respecté pour permettre un binaire OpenCode personnalisé.

## `oc acp` vs `oc runner`

Les deux ont des rôles différents :

- `oc acp` : accès direct au serveur ACP natif OpenCode ;
- `oc runner` : abstraction toolkit pour l'orchestration V2 et les futurs runtimes.

On garde donc `oc acp` totalement compatible.

## API cible inspirée d'Octop

Le prochain niveau implémentera une session ACP contrôlée avec les opérations conceptuelles :

```text
list
start
message
respond
status
close
```

Cette API permettra :

- de démarrer un enfant ;
- de continuer sa session ;
- de remonter une demande de permission au parent ;
- de connaître l'état d'un job ;
- de fermer proprement le runner.

## Permissions

Un runner enfant ne doit jamais devenir un moyen de contourner les permissions du parent.

Règles :

- liste de runners explicitement approuvée ;
- aucun shell arbitraire fourni par le modèle pour créer un runner ;
- cwd limité au workspace prévu ;
- permissions ACP remontées au parent ;
- pas de runner sortant si son mode d'exécution contourne une isolation active ;
- secrets non ajoutés automatiquement à l'environnement d'un enfant.

Ce point reprend notamment le durcissement réalisé par Octop pour empêcher un runner ACP lancé sur l'hôte de contourner un sandbox de répertoire.

## Parallélisme

Le runner manager sera utilisé par le job pool V2 :

```text
orchestrator
  └── bounded job pool
        ├── runner A
        ├── runner B
        └── runner C
```

Le nombre de jobs parallèles restera borné et configurable.

L'ACP ne doit pas recréer des conversations libres entre agents : le parent reste responsable du routage et du handoff.
