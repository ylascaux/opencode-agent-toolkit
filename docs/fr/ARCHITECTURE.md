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
       -> docs-writer
```

Le lead ne sélectionne que les domaines utiles. Lorsqu’une documentation durable est demandée, `platform-architect` stabilise d’abord le design puis délègue l’écriture du fichier à `docs-writer` ; le lead architecture reste non-editing.

## Review d’architecture indépendante

La production d’architecture est volontairement découpée en étapes :

```text
platform-architect
      |
      v
artefact d’architecture terminé
      |
      +--------------------+
      |                    |
      v                    v
 review-lead          security-lead
 review indépendante  gate sécurité adaptatif
      |                    |
      +---------+----------+
                |
                v
          synthèse finale
```

`review-lead` doit revalider l’artefact à partir des preuves directes du repository au lieu d’accepter le handoff du producteur comme preuve. Il peut utiliser `project-scanner` puis uniquement les dimensions Platform pertinentes : AWS, Kubernetes, SRE, observabilité, FinOps, base de données, networking et sécurité IaC.

Si l’artefact terminé modifie des trust boundaries, IAM, l’exposition publique, les secrets ou la posture de sécurité de l’infrastructure, `security-lead` devient un gate supplémentaire. La review indépendante et le gate sécurité doivent fonctionner en parallèle lorsqu’ils lisent le même artefact terminé et qu’aucun ne dépend du résultat de l’autre.

Le chemin producteur `platform-architect` ne joue jamais le rôle de reviewer indépendant final de son propre artefact.

## Architecture pilotée par les preuves

Les recommandations séparent faits observés, signaux heuristiques, hypothèses et décisions proposées. L’inventaire projet V2 contient composants, interfaces, ressources AWS, data stores, signaux, preuves fichier/ligne, confiance et relations accompagnées de preuves.

Une flèche d’un diagramme doit être appuyée par une preuve ou clairement marquée comme proposée/hypothétique.

Le handoff prêt pour review doit contenir le chemin de l’artefact, les décisions importantes, les alternatives rejetées, les hypothèses, la carte des preuves, migration/rollback, risques résiduels et sujets d’ownership/opérabilité.

## Sortie attendue

Pour une architecture Platform non triviale : contexte/contraintes, état actuel/cible, flux composants/données/contrôle, trust boundaries, modèle disponibilité/SLO, scaling/capacité, failure domains, contrôles sécurité, ownership opérationnel, upgrades/migrations/rollback, DR/RTO/RPO si pertinent, coûts principaux, matrice de décision/alternatives rejetées et risques résiduels.

Utilise `/architecture-review` lorsqu’un artefact d’architecture existant doit être revu indépendamment sans relancer d’abord une nouvelle phase de design.
