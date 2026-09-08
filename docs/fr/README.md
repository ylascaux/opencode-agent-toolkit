# Documentation

Le toolkit est un système d’ingénierie à 37 agents avec un plan de contrôle peu profond et auditable.

## Ordre de lecture conseillé

1. [Architecture système du toolkit](SYSTEM_ARCHITECTURE.md) — **commence ici pour comprendre le fonctionnement global**
2. [Installation](INSTALLATION.md)
3. [Architecture des agents](AGENTS.md)
4. [Routage](ROUTING.md)
5. [Stratégie des modèles](MODEL_STRATEGY.md)
6. [Fiabilité et garde-fous](RELIABILITY.md)
7. [Utilisation](USAGE.md)
8. [Sécurité](SECURITY.md)
9. [Workflow d’architecture produit par les agents](ARCHITECTURE.md)
10. [Découverte des projets](PROJECT_DISCOVERY.md)
11. [Compatibilité OpenCode](OPENCODE_COMPATIBILITY.md)

`SYSTEM_ARCHITECTURE.md` décrit le toolkit lui-même : boot `oc`, génération des configs, control plane, délégation, modèles, watchdog, queue de sous-agents, failure modes et points d’extension. `ARCHITECTURE.md` décrit quant à lui le workflow utilisé pour concevoir et reviewer l’architecture d’un projet cible.

Les deux contrats lisibles par machine sont dans `contracts/` :
- `agent-handoff.schema.json`
- `routing-decision.schema.json`
