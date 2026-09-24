# OpenCode Agent Toolkit V2

## Objectif

La branche `v1` fige l'implémentation actuelle du toolkit.

La branche `main` devient la ligne de développement **V2**. La V2 doit rester fidèle au principe du projet : améliorer fortement l'expérience OpenCode sans transformer le toolkit en plateforme à maintenir.

Les deux axes prioritaires documentés ici sont :

1. une **mémoire partagée multi-machine** basée sur PostgreSQL et inspirée de `harness-memory` / Octop ;
2. une orchestration multi-agent simple et bornée, sans réintroduire une explosion du nombre d'agents.

## Principes V2

- OpenCode 2 reste le runtime principal.
- Le catalogue reste volontairement réduit aux agents permanents utiles.
- Les spécialisations restent des skills/capacités, pas des agents permanents.
- Pas de serveur web, dashboard ou control plane Octop dans le toolkit.
- Pas de duplication d'un framework complet si une petite intégration suffit.
- Les états partagés doivent avoir une source de vérité explicite.
- Les composants distants doivent pouvoir être désactivés avec un fallback local propre.
- La mémoire V2 démarre proprement : **aucune migration automatique de la mémoire V1 n'est prévue**.

## Documents

- [Mémoire partagée V2](shared-memory.md)
- [Plan d'implémentation](implementation-plan.md)

## Référence Octop

La V2 s'inspire de plusieurs choix d'architecture du projet TencentCloud/Octop sans importer Octop lui-même comme runtime.

Références principales :

- https://github.com/TencentCloud/Octop/blob/main/src/octop/infra/agents/memory_backend.py
- https://github.com/TencentCloud/Octop/blob/main/src/octop/api/routers/memory_portable.py
- https://github.com/TencentCloud/Octop/blob/main/docs/configuration.md
- https://github.com/TencentCloud/Octop/blob/main/docs/adr/002-database-backends.md
- https://github.com/TencentCloud/Octop/blob/main/docs/architecture.md
