# Architecture

## Conseil d’architecture

```text
meta-router
  -> platform-architect
       -> project-scanner
       -> architecture-designer
       -> aws-platform
       -> terraform-terragrunt
       -> kubernetes
       -> cicd
       -> networking
       -> database
       -> sre
       -> observability
       -> finops
       -> threat-model
       -> iac-security
```

Le lead ne sélectionne que les domaines utiles.

## Architecture pilotée par les preuves

Les recommandations séparent faits observés, signaux heuristiques, hypothèses et décisions proposées. L’inventaire projet V2 contient composants, interfaces, ressources AWS, data stores, signaux, preuves fichier/ligne, confiance et relations accompagnées de preuves.

Une flèche d’un diagramme doit être appuyée par une preuve ou clairement marquée comme proposée/hypothétique.

## Sortie attendue

Pour une architecture Platform non triviale : contexte/contraintes, état actuel/cible, flux composants/données/contrôle, trust boundaries, modèle disponibilité/SLO, scaling/capacité, failure domains, contrôles sécurité, ownership opérationnel, upgrades/migrations/rollback, DR/RTO/RPO si pertinent, coûts principaux, matrice de décision/alternatives rejetées et risques résiduels.
