# Pipeline de sécurité

La sécurité est une pipeline de review indépendante, pas une option du builder.

```text
meta-router
  -> security-lead
       -> threat-model
       -> appsec
       -> iac-security
       -> supply-chain
       -> secrets
       -> pentest
```

`security-lead` sélectionne uniquement les gates liés à la surface d’attaque réellement modifiée.

- `threat-model` : assets, acteurs, points d’entrée, trust boundaries et scénarios d’abus.
- `appsec` : authn/authz, injections, SSRF, traversal, désérialisation, XSS/CSRF, uploads, crypto, rate limits et logique métier.
- `iac-security` : IAM, exposition publique, chiffrement/KMS, policies, workload identity/RBAC, state et logs.
- `supply-chain` : dépendances, lockfiles, actions CI, images, provenance et preuve de vulnérabilité liée aux versions réellement utilisées.
- `secrets` : credentials/valeurs sensibles avec contenu masqué.
- `pentest` : validation runtime uniquement sur une cible explicitement autorisée et dans le scope.

Le pentest interdit persistance, exfiltration, DoS, credential spraying, mouvement latéral, furtivité et modifications destructives.

## Politique des outils

Les agents de review sécurité ne modifient pas le code. Les outils de sécurité et l’accès Web sont soumis à une politique explicite/validation ; secrets et pentest ont le Web désactivé par défaut. Tous les agents refusent les chemins classiques `.env`, clés, SSH et credentials AWS.

## Contrat d’un finding

Un finding contient sévérité, confiance, preuve directe, conditions d’exploitation, impact, remédiation et étape de vérification. Une vulnérabilité exploitable doit être distinguée d’une recommandation de hardening.
