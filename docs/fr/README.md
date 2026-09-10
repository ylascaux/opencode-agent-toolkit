# Documentation

Le toolkit est un système d’ingénierie à 40 agents avec un plan de contrôle peu profond et auditable.

## Ordre de lecture conseillé

1. [Architecture système du toolkit](SYSTEM_ARCHITECTURE.md) — **commence ici pour comprendre le fonctionnement global**
2. [Configuration des agents](CONFIGURATION_AGENTS.md) — format autonome `agents/<nom>/`
3. [Architecture des agents](AGENTS.md)
4. [Installation](INSTALLATION.md)
5. [Utilisation](USAGE.md)
6. [Stratégie des modèles](MODEL_STRATEGY.md)
7. [Permissions](PERMISSIONS.md)
8. [Fiabilité et garde-fous](RELIABILITY.md)
9. [Routage](ROUTING.md)
10. [Sécurité](SECURITY.md)
11. [Sandbox et diagnostics cloud manuels](SANDBOX.md)
12. [Workflow d’architecture produit par les agents](ARCHITECTURE.md)
13. [Découverte des projets](PROJECT_DISCOVERY.md)
14. [Pipeline de recherche structurée](RESEARCH_PIPELINE.md)
15. [Compatibilité OpenCode](OPENCODE_COMPATIBILITY.md)
16. [Durcissement runtime](RUNTIME_HARDENING.md)

`SYSTEM_ARCHITECTURE.md` décrit le toolkit lui-même : boot `oc`, génération des configs, control plane, délégation, modèles, watchdog, queue de sous-agents, failure modes et points d’extension. `CONFIGURATION_AGENTS.md` décrit la source de vérité éditable de chaque agent. `ARCHITECTURE.md` décrit le workflow utilisé pour concevoir et reviewer l’architecture d’un projet cible. `RESEARCH_PIPELINE.md` décrit les agents de recherche génériques, les enveloppes de jobs/résultats et la frontière avec un orchestrateur externe. `SANDBOX.md` décrit l’isolation des commandes de développement et le flux manuel pour AWS/Kubernetes.

Les contrats lisibles par machine sont dans `contracts/` :
- `agent-handoff.schema.json`
- `routing-decision.schema.json`
- `research-job.schema.json`
- `research-result.schema.json`
