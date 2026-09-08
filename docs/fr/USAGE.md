# Utilisation

Lancer le toolkit avec `just run`. Utiliser `/auto` pour laisser le routage choisir automatiquement.

## Delivery

```text
/ship Ajoute l’idempotence à ce consumer d’événements.
```

Le meta-router délègue à `orchestrator`, qui choisit les leaf agents d’implémentation/tests/review/sécurité. L’agent qui code ne valide jamais seul son propre travail.

## Review

```text
/review Review la branche courante avant merge.
```

Le travail passe par `review-lead`, qui ne sélectionne que les dimensions pertinentes.

## Architecture

```text
/architecture Analyse les systèmes sous ~/Projects et propose une architecture Platform AWS cible.
```

Le travail part directement vers `platform-architect`, ce qui conserve une profondeur de délégation de deux niveaux.

## Sécurité

```text
/security Review les changements d’authentification et Terraform de cette branche.
```

Le travail passe par `security-lead`. Le pentest runtime n’est utilisé que lorsqu’une cible autorisée est explicite.

## Handoff des preuves

Les agents délégués terminent avec STATUS, SUMMARY, FACTS, ASSUMPTIONS, EVIDENCE, FINDINGS, RESIDUAL RISKS, RECOMMENDED NEXT AGENTS et CONFIDENCE. HIGH signifie directement vérifié/reproduit, MEDIUM une preuve statique ou indirecte forte, LOW une hypothèse non résolue ou une preuve manquante.

## Configuration des modèles

```bash
just configure
just models
```

Quand le gateway le permet, utiliser des familles de modèles différentes entre builder et reviewer/sécurité réduit les angles morts corrélés.
