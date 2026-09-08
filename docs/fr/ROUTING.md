# Routage

Le router optimise le **chemin suffisant le moins coûteux**, pas le nombre minimal d’agents à tout prix.

## Dimensions de décision

Avant délégation, `meta-router` classe domaines, complexité, risque, incertitude, blast radius et type de changement. La forme lisible par machine est `contracts/routing-decision.schema.json`.

## Routes principales

```text
implémentation / fix / incident -> orchestrator
review                          -> review-lead
architecture / platform / coût -> platform-architect
évaluation sécurité            -> security-lead
désaccord matériel             -> arbiter
risque élevé / confiance basse -> deep-reasoner
preuves faibles                -> evidence-auditor
```

## Profondeur de délégation

```text
meta-router -> lead/orchestrator -> leaf
```

Un lead n’appelle pas un autre lead. Un leaf ne peut appeler aucun sous-agent. `subagent_depth=2` reste donc suffisant.

## Routage des reviews

`review-lead` part de la surface réellement modifiée et ne lance que les dimensions pertinentes : logique Go -> reviewer ; contrat HTTP public -> reviewer + API contract + AppSec pertinent ; migration SQL -> reviewer + database ; Terraform ingress/WAF/IAM -> reviewer + networking + IaC security.

## Escalade

`arbiter` sert uniquement aux conflits matériels entre conclusions crédibles. `deep-reasoner` intervient pour les décisions coûteuses/difficiles à inverser, les risques high/critical, les preuves incomplètes ou la confiance basse persistante. `evidence-auditor` vérifie les affirmations de réussite non triviales.
