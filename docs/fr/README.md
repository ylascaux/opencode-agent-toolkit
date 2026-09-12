# Documentation

Le toolkit est un système d’ingénierie multi-agents avec un plan de contrôle peu profond et auditable.

## Ordre de lecture conseillé

1. [Architecture système du toolkit](SYSTEM_ARCHITECTURE.md) — **commence ici pour comprendre le fonctionnement global**
2. [Architecture multi-runtime](MULTI_RUNTIME.md) — source de vérité indépendante du runtime et stratégie de migration
3. [Adapter Codex](CODEX_ADAPTER.md) — contrat Codex, mapping modèles/reasoning, mémoire et ressources distantes optionnelles
4. [Workflow cross-runtime](CROSS_RUNTIME_WORKFLOW.md) — passer proprement d'OpenCode à Codex ou à un assistant connecté à GitHub
5. [Configuration des agents](CONFIGURATION_AGENTS.md) — format autonome `agents/<nom>/`
6. [Architecture des agents](AGENTS.md)
7. [Installation](INSTALLATION.md)
8. [Utilisation](USAGE.md)
9. [Stratégie des modèles](MODEL_STRATEGY.md)
10. [Permissions](PERMISSIONS.md)
11. [Fiabilité et garde-fous](RELIABILITY.md)
12. [Routage](ROUTING.md)
13. [Sécurité](SECURITY.md)
14. [Sandbox et diagnostics cloud manuels](SANDBOX.md)
15. [Workflow d’architecture produit par les agents](ARCHITECTURE.md)
16. [Découverte des projets](PROJECT_DISCOVERY.md)
17. [Pipeline de recherche structurée](RESEARCH_PIPELINE.md)
18. [Worker de recherche externe](RESEARCH_WORKER.md)
19. [Compatibilité OpenCode](OPENCODE_COMPATIBILITY.md)
20. [Durcissement runtime](RUNTIME_HARDENING.md)

`SYSTEM_ARCHITECTURE.md` décrit le toolkit lui-même : boot `oc`, génération des configs, control plane, délégation, modèles, watchdog, queue de sous-agents, failure modes et points d’extension. `MULTI_RUNTIME.md` définit la future source de vérité portable et la migration incrémentale vers plusieurs runtimes. `CODEX_ADAPTER.md` fixe le contrat de l'adapter Codex sans dupliquer les agents. `CROSS_RUNTIME_WORKFLOW.md` définit comment reprendre une tâche depuis Git/PR plutôt que depuis l'historique d'un chat. `CONFIGURATION_AGENTS.md` décrit la source de vérité éditable de chaque agent. `ARCHITECTURE.md` décrit le workflow utilisé pour concevoir et reviewer l’architecture d’un projet cible. `RESEARCH_PIPELINE.md` décrit les agents de recherche génériques, les enveloppes de jobs/résultats et la frontière avec un orchestrateur externe. `RESEARCH_WORKER.md` décrit le worker pull HTTPS authentifié qui exécute ces jobs via OpenCode sans exposer de service entrant sur la machine worker. `SANDBOX.md` décrit l’isolation des commandes de développement et le flux manuel pour AWS/Kubernetes.

Les contrats lisibles par machine sont dans `contracts/` :
- `agent-handoff.schema.json`
- `routing-decision.schema.json`
- `research-job.schema.json`
- `research-result.schema.json`
