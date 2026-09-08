# Pipeline sécurité

La sécurité est un plan de review indépendant afin que l’agent qui produit un changement ne soit pas le seul à juger sa sécurité.

## Contrôles

1. `threat-model` : actifs, acteurs, points d’entrée, trust boundaries, abuse cases et mitigations.
2. `appsec` : authentification/autorisation, injections, SSRF, path traversal, désérialisation, XSS/CSRF, uploads, redirects, données sensibles, crypto et logique métier.
3. `iac-security` : IAM, exposition publique, chiffrement, KMS, security groups, bucket policies, logging, workload identity, RBAC Kubernetes, privilèges pods et sécurité du state Terraform.
4. `supply-chain` : dépendances, lockfiles, permissions CI, provenance des images, pinning des actions et intégrité du build.
5. `secrets` : credentials et données sensibles accidentellement exposés ; les valeurs doivent rester masquées.
6. `pentest` : validation runtime autorisée d’une vulnérabilité plausible avec la preuve minimale nécessaire.

## Sélection adaptative

Tous les changements ne déclenchent pas tous les contrôles. Le routeur choisit selon la surface d’attaque :

- nouveau flux API/auth : threat-model + AppSec ;
- Terraform/EKS : threat-model si les trust boundaries changent + IaC security ;
- dépendance ou CI : supply-chain ;
- suspicion de fuite de credential : secrets ;
- question d’exploitabilité runtime : pentest uniquement sur une cible explicitement autorisée.

## Sécurité du pentest

Le scope doit être explicite. Les cibles privilégiées sont localhost, les environnements de test ou les fixtures fournies. L’agent ne doit pas maintenir un accès, exfiltrer des données, effectuer de DoS, credential spraying, mouvement latéral, furtivité ou action destructive. Il s’arrête dès que la preuve minimale est obtenue.

Les permissions par défaut autorisent seulement quelques `curl` localhost sans confirmation ; les autres commandes shell demandent une approbation.

## Qualité des findings

Chaque finding doit contenir :

- composant/localisation ;
- preuve ;
- conditions d’exploitation ;
- impact ;
- sévérité et confiance ;
- remédiation ;
- étapes de vérification ;
- risque résiduel.

Les recommandations de hardening doivent être séparées des vulnérabilités réellement exploitables.

## Sécurité Terraform

Le formatage et la validation Terraform/OpenTofu/Terragrunt peuvent être autorisés automatiquement ; les plans demandent confirmation ; `apply` et `destroy` sont refusés par défaut.
