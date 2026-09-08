# OpenCode Agent Toolkit — Guide français

Ce toolkit transforme OpenCode en système d’ingénierie multi-agent orienté coût, preuves et sécurité, pour le développement logiciel, le Platform Engineering, AWS, Terraform/Terragrunt, Python, Go, la fiabilité et la sécurité.

## Principe

Le point d’entrée par défaut est `meta-router`. Il classe chaque demande selon le domaine, la complexité, le risque, l’incertitude et le blast radius, puis choisit le chemin minimal suffisant. Les tâches simples restent économiques ; les tâches complexes ou risquées sont escaladées.

```text
Utilisateur
   |
   v
meta-router
   |-- tâche simple ------------------> spécialiste ciblé
   |-- implémentation ----------------> orchestrator -> build/test/review/security
   |-- architecture ------------------> conseil d’architecture
   |-- désaccord ---------------------> arbiter
   |-- risque élevé / confiance basse -> deep-reasoner
   `-- preuve de complétion ----------> evidence-auditor
```

## Capacités principales

- 35 agents configurables indépendamment.
- Mapping `MODEL_*` par agent pour LiteLLM/Smart Router ou un autre provider compatible.
- Routage adaptatif plutôt que lancement systématique de tous les agents.
- Review indépendante de la correction, de la sécurité et des preuves.
- Conseil d’architecture AWS/Platform.
- Garde-fous Terraform/Terragrunt.
- Pentest autorisé, limité et non destructif.
- Découverte multi-repositories en lecture seule via `PROJECTS_ROOT`.
- Compatibilité OpenCode V1 stable et OpenCode 2 beta.
- Installation en une commande via `just install`.

## Parcours recommandé

1. [Installation](INSTALLATION.md)
2. [Utilisation](USAGE.md)
3. [Routage et stratégie de modèles](ROUTING.md)
4. [Architecture](ARCHITECTURE.md)
5. [Agents](AGENTS.md)
6. [Sécurité](SECURITY.md)
7. [Découverte des projets](PROJECT_DISCOVERY.md)
8. [Compatibilité OpenCode](OPENCODE_COMPATIBILITY.md)
