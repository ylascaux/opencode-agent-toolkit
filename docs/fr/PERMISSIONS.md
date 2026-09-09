# Permissions des agents

Les permissions OpenCode effectives sont configurées dans `agents/permissions/`.

- `_default.json` contient le socle commun.
- `<agent>.json` surcharge ce socle pour un agent donné.
- Exécute `just config` après une modification.

La politique par défaut privilégie désormais l’utilisabilité tout en conservant des garde-fous explicites :

- `websearch` : `allow`
- `webfetch` : `allow`
- commandes shell inconnues/non destructives : `ask`
- commandes Git en lecture seule : `allow`
- modification de fichiers : `ask` par défaut, `allow` pour les agents d’implémentation
- lecture de fichiers sensibles comme `.env`, clés SSH ou credentials AWS : `ask`
- répertoires externes : `ask`; `project-scanner` dispose de `~/Projects/**` en `allow`
- opérations clairement destructives comme suppression récursive, force-push, hard reset/clean, Terraform/OpenTofu/Terragrunt apply/destroy, Kubernetes delete et opérations similaires : `deny`

La hiérarchie task/subagent générée reste un garde-fou structurel déterministe. Elle ne change que si un fichier de permissions d’agent surcharge explicitement `task`.
