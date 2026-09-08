# Utilisation

Les principaux points d’entrée sont des commandes haut niveau routées par `meta-router`.

## `/auto`

Routage adaptatif général :

```text
/auto Review ce service et indique ce qui doit être amélioré avant la production.
```

À utiliser lorsque tu ne veux pas choisir toi-même le workflow.

## `/ship`

Workflow d’implémentation :

```text
/ship Ajoute l’idempotence à ce webhook et les tests associés.
```

Parcours typique : classification -> plan si nécessaire -> spécialiste d’implémentation -> tests -> review indépendante -> contrôles sécurité pertinents -> audit des preuves.

## `/review`

Review indépendante d’une branche, d’un changement ou d’un composant :

```text
/review Review le diff courant pour la correction, la compatibilité, la sécurité et les régressions de performance.
```

Les spécialistes API-contract, database, networking ou performance ne sont ajoutés que si nécessaire.

## `/architecture`

Conseil d’architecture :

```text
/architecture Analyse les services dans ~/Projects et propose une architecture AWS cible avec migration et rollback.
```

Le workflow peut combiner découverte des projets, platform architect, AWS, Kubernetes, Terraform, database, networking, SRE, observability, FinOps et sécurité.

## `/security`

Review sécurité adaptative :

```text
/security Review ce changement Terraform + API et valide les problèmes exploitables sur localhost lorsque pertinent.
```

Le pentest reste explicitement autorisé, limité et non destructif.

## `/debug`

Debug basé sur les preuves :

```text
/debug Trouve la root cause de ce timeout et ajoute un test de régression.
```

Le debugger classe puis falsifie les hypothèses avant d’appliquer une correction minimale.

## `/incident`

Workflow incident :

```text
/incident Analyse l’augmentation des 5xx API depuis le dernier déploiement.
```

Le routeur utilise debugger, SRE, observability et les spécialistes concernés. Il sépare faits et hypothèses, définit le blast radius, la mitigation/rollback et les actions de suivi.

## `/cost`

Workflow FinOps/performance :

```text
/cost Analyse cette plateforme EKS et identifie les économies principales sans réduire la fiabilité.
```

## Appels directs

Tu peux toujours appeler un spécialiste directement :

```text
@terraform-terragrunt Review ce module.
@appsec Review ce flux d’authentification.
@project-scanner Inventorie ~/Projects.
```

Utilise les appels directs pour les tâches ciblées et les commandes haut niveau lorsque coordination, indépendance ou escalade sont importantes.
