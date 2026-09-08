# Découverte des projets

Le scanner lit les projets sous `PROJECTS_ROOT` (par défaut `$HOME/Projects`) et produit un inventaire normalisé avec `just scan`.

## Inventaire v2

Chaque projet contient métadonnées repository/git, comptage des langages, manifests, type de composant inféré, définitions API/interfaces détectées, ressources AWS avec preuves, data stores, signaux IaC/CI/container/Kubernetes, preuves avec fichier et numéro de ligne si disponible, et confiance.

Les `relationships` globaux sont volontairement conservateurs. Une heuristique faible basée sur un nom reste LOW confidence ; le scanner préfère ne produire aucune relation plutôt que d’inventer une flèche d’architecture.

Exemple :

```json
{
  "kind": "aws_service",
  "value": "S3",
  "file": "infra/main.tf",
  "line": 42,
  "confidence": "medium"
}
```

Les agents d’architecture valident les signaux heuristiques avant de les considérer comme des faits.

## API locale

```bash
just api
curl -sS -X POST http://127.0.0.1:8765/scan -H 'content-type: application/json' -d '{}' > architecture-inventory.json
```

L’API reste limitée au dossier projets configuré.
