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

Le workflow est découpé en étapes et évite l’auto-review :

1. `meta-router` route le design et la collecte de preuves vers `platform-architect`.
2. Si un document durable est demandé, `platform-architect` délègue l’écriture du fichier à `docs-writer` une fois le design stabilisé.
3. Une fois l’artefact terminé, `meta-router` le route vers `review-lead` pour une review indépendante adossée aux preuves du repository.
4. Si les trust boundaries, IAM, l’exposition publique, les secrets ou la posture de sécurité de l’infrastructure changent de manière significative, `security-lead` devient un gate supplémentaire. Il peut fonctionner en parallèle avec `review-lead` si les deux ne font que lire le même artefact terminé.
5. La synthèse finale présente les preuves, trade-offs, alternatives rejetées, migration/rollback et risques résiduels.

Le chemin qui produit l’architecture n’effectue pas lui-même la review indépendante finale.

Pour revoir un artefact d’architecture existant sans relancer d’abord une phase de design :

```text
/architecture-review Review docs/architecture/aws-platform.md par rapport au repository actuel.
```

Cette commande passe par `review-lead`, qui peut reconstruire les faits avec `project-scanner` et ne sélectionner que les dimensions Platform/sécurité utiles.

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
