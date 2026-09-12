# Documentation

Le toolkit est un système d’ingénierie multi-agents avec un plan de contrôle peu profond et auditable, désormais partagé entre OpenCode et Codex à partir d’une source canonique commune.

## Ordre de lecture conseillé

1. [Architecture système du toolkit](SYSTEM_ARCHITECTURE.md) — **commence ici pour comprendre le fonctionnement global**
2. [Architecture multi-runtime](MULTI_RUNTIME.md) — source de vérité indépendante du runtime et architecture actuelle
3. [Adapter Codex](CODEX_ADAPTER.md) — contrat Codex, mapping modèles/reasoning et mémoire
4. [Workflow cross-runtime](CROSS_RUNTIME_WORKFLOW.md) — passer proprement d'OpenCode à Codex ou à un assistant connecté à GitHub
5. [Configuration des agents](CONFIGURATION_AGENTS.md) — format autonome `agents/<nom>/`
6. [Architecture des agents](AGENTS.md)
7. [Installation](INSTALLATION.md)
8. [Utilisation](USAGE.md)
9. [Runtime acceptance (anglais)](../en/RUNTIME_ACCEPTANCE.md) — acceptance E2E isolée et contrats validés
10. [Processus de release](RELEASE.md) — versioning, gates et procédure de tag
11. [Stratégie des modèles](MODEL_STRATEGY.md)
12. [Permissions](PERMISSIONS.md)
13. [Fiabilité et garde-fous](RELIABILITY.md)
14. [Routage](ROUTING.md)
15. [Sécurité](SECURITY.md)
16. [Sandbox et diagnostics cloud manuels](SANDBOX.md)
17. [Workflow d’architecture produit par les agents](ARCHITECTURE.md)
18. [Découverte des projets](PROJECT_DISCOVERY.md)
19. [Pipeline de recherche structurée](RESEARCH_PIPELINE.md)
20. [Worker de recherche externe](RESEARCH_WORKER.md)
21. [Compatibilité OpenCode](OPENCODE_COMPATIBILITY.md)
22. [Durcissement runtime](RUNTIME_HARDENING.md)

`SYSTEM_ARCHITECTURE.md` décrit le toolkit lui-même : boot `oc`, génération des configs, control plane, délégation, modèles, watchdog, queue de sous-agents, failure modes et points d’extension. `MULTI_RUNTIME.md` décrit la source de vérité portable utilisée par OpenCode et Codex. `CODEX_ADAPTER.md` fixe le contrat de l'adapter Codex sans dupliquer les agents. `CROSS_RUNTIME_WORKFLOW.md` définit comment reprendre une tâche depuis Git/PR plutôt que depuis l'historique d'un chat. `CONFIGURATION_AGENTS.md` décrit la source de vérité éditable de chaque agent. `ARCHITECTURE.md` décrit le workflow utilisé pour concevoir et reviewer l’architecture d’un projet cible. `RESEARCH_PIPELINE.md` décrit les agents de recherche génériques, les enveloppes de jobs/résultats et la frontière avec un orchestrateur externe. `RESEARCH_WORKER.md` décrit le worker pull HTTPS authentifié qui exécute ces jobs via OpenCode sans exposer de service entrant sur la machine worker. `SANDBOX.md` décrit l’isolation des commandes de développement et le flux manuel pour AWS/Kubernetes. `RELEASE.md` décrit comment préparer puis taguer une version depuis le commit mergé sur `main`.

Les contrats lisibles par machine sont dans `contracts/` :
- `agent-handoff.schema.json`
- `routing-decision.schema.json`
- `research-job.schema.json`
- `research-result.schema.json`
