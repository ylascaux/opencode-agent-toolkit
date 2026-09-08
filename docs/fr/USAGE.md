# Utilisation

Pour un usage local au repo du toolkit, utilise `just run`. Pour un usage quotidien depuis n’importe quel workspace, installe une seule fois la commande utilisateur réversible avec `just install-user`, puis lance `oc` depuis le projet sur lequel OpenCode doit travailler.

```bash
cd ~/Projects/my-api
oc
```

Le launcher conserve le répertoire courant. Le repo du toolkit fournit la configuration OpenCode générée et les mappings de modèles ; le dossier depuis lequel tu lances `oc` reste le workspace OpenCode.

Utilise `/auto` pour laisser le routage choisir automatiquement.

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

## Profils de modèles

Le profil de travail par défaut est GitHub Copilot avec Luna/Terra/Sol mappés vers LOW/MEDIUM/HIGH.

```bash
just models
just profile copilot
just profile codex
```

Utilise `.env.local` pour les overrides persistants par agent :

```bash
MODEL_BUILDER=openai/gpt-5.3-codex
```

Le profil actif choisit uniquement les modèles concrets des tiers ; le routage, les permissions et les politiques de sécurité des agents restent identiques.

## Cycle de vie de la commande utilisateur

```bash
just install-user      # crée ~/.local/bin/oc
just user-status       # vérifie le lien
just uninstall-user    # le supprime seulement s’il appartient à ce toolkit
```

Choisis un autre nom de commande si nécessaire :

```bash
just install-user opencode-agents
```
