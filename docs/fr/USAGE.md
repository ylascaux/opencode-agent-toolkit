# Utilisation

Pour un usage local au repo du toolkit, utilise `just run`. Pour un usage quotidien depuis n’importe quel workspace, installe une seule fois la commande utilisateur réversible avec `just install-user`, puis lance `oc` depuis le projet sur lequel OpenCode doit travailler.

```bash
cd ~/Projects/my-api
oc
```

Le launcher conserve le répertoire courant. Le repo du toolkit fournit la configuration OpenCode générée et les mappings de modèles ; le dossier depuis lequel tu lances `oc` reste le workspace OpenCode.

Utilise `/auto` pour laisser le routage choisir automatiquement.

## Validation du plan

La politique runtime par défaut est `PLAN_APPROVAL_MODE=changes`. La découverte et l’analyse en lecture seule peuvent démarrer immédiatement, mais le toolkit doit présenter un plan concret et attendre une validation explicite avant de modifier des fichiers, l’état Git, l’infrastructure, la configuration ou un autre système externe.

Une modification normale ressemble donc à ceci :

```text
/ship Ajoute l’idempotence à ce consumer d’événements.
```

OpenCode collecte le minimum de preuves nécessaire pour planifier, puis retourne un plan terminé par :

```text
PLAN_APPROVAL_REQUIRED
```

Réponds avec une validation courte et explicite comme `go`, `approve`, `oui` ou `valide` pour exécuter ce plan. Toute autre réponse est considérée comme un changement de périmètre et impose un plan révisé. `reject`, `non`, `stop` ou `annule` rejette le plan courant.

Tu peux demander explicitement un plan sans exécution :

```text
/plan Ajoute l’idempotence à ce consumer d’événements.
```

Si l’implémentation découvre un changement matériel de périmètre, de dépendance, de trust boundary, d’étape destructive, de rollback ou de validation, l’exécution s’arrête et le plan révisé se termine par :

```text
PLAN_REAPPROVAL_REQUIRED
```

La validation est limitée à la demande racine courante et à ses sous-agents. Une nouvelle demande utilisateur réinitialise automatiquement l’autorisation.

Configure le comportement dans `.env` ou `.env.local` :

```bash
PLAN_APPROVAL_MODE=changes   # défaut
# PLAN_APPROVAL_MODE=off     # désactive le gate
# PLAN_APPROVAL_MODE=always  # gate aussi la délégation au-delà de la découverte directe
```

La frontière plan/exécution est imposée par des plugins runtime pour OpenCode V1 et V2. Les prompts améliorent le workflow, mais un outil mutateur reste bloqué lorsqu’aucun plan approuvé n’existe.

## Delivery

```text
/ship Ajoute l’idempotence à ce consumer d’événements.
```

Le meta-router délègue la planification à `orchestrator`, qui choisit les leaf agents d’implémentation/tests/review/sécurité. Le plan est présenté à l’utilisateur racine avant le début de l’implémentation. Après validation, l’orchestrateur n’exécute que le périmètre approuvé. L’agent qui code ne valide jamais seul son propre travail.

## Review

```text
/review Review la branche courante avant merge.
```

Le travail passe par `review-lead`, qui ne sélectionne que les dimensions pertinentes. Une review purement en lecture seule ne nécessite pas de validation de plan.

## Architecture

```text
/architecture Analyse les systèmes sous ~/Projects et propose une architecture Platform AWS cible.
```

Le workflow est découpé en étapes et évite l’auto-review :

1. `meta-router` route le design et la collecte de preuves vers `platform-architect`.
2. Si un document durable ou un autre artefact doit être créé/modifié, le plan d’écriture/migration stabilisé est présenté pour validation avant toute mutation.
3. Après validation, `platform-architect` délègue l’écriture du fichier à `docs-writer` une fois le design stabilisé.
4. Une fois l’artefact terminé, `meta-router` le route vers `review-lead` pour une review indépendante adossée aux preuves du repository.
5. Si les trust boundaries, IAM, l’exposition publique, les secrets ou la posture de sécurité de l’infrastructure changent de manière significative, `security-lead` devient un gate supplémentaire. Il peut fonctionner en parallèle avec `review-lead` si les deux ne font que lire le même artefact terminé.
6. La synthèse finale présente les preuves, trade-offs, alternatives rejetées, migration/rollback et risques résiduels.

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
