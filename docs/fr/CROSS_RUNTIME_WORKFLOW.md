# Workflow cross-runtime

## Pourquoi ce document existe

Le toolkit doit permettre de déplacer le travail entre OpenCode, Codex et un assistant connecté à GitHub sans créer trois sources de vérité incompatibles.

Le dépôt possède la politique d'ingénierie. Le plugin mémoire possède la mémoire contextuelle durable. Chaque runtime n'est qu'une surface d'exécution.

```text
                           dépôt Git
                 code canonique + politique agents
                              /   |   \
                             /    |    \
                            v     v     v
                      OpenCode  Codex  ChatGPT/GitHub
                            \     |     /
                             \    |    /
                              v   v   v
                         pull requests / reviews
                                 |
                                 v
                      opencode-memory-plugin
```

## Où stocker quoi

### `opencode-agent-toolkit`

Ici vivent les comportements d'ingénierie durables et partageables :

- rôles des agents ;
- prompts ;
- topologie parent/enfant ;
- intention des permissions ;
- tiers de modèles ;
- politique de fiabilité ;
- code des adapters runtime ;
- schémas/contrats ;
- documentation ;
- tests.

### `opencode-memory-plugin`

Ici vivent les comportements de mémoire :

- extraction des candidates ;
- quarantaine des candidates ;
- résolution des projets ;
- rendu du contexte ;
- règles de promotion ;
- cycle Git du vault privé ;
- future surface MCP mémoire.

### Dépôt mémoire privé

Ici vivent les informations privées et durables :

- décisions projet ;
- faits importants à conserver entre sessions ;
- préférences de travail ;
- hats/personas ;
- contexte cross-project validé.

### État local/généré du runtime

Ici vivent les données jetables :

- configuration runtime générée ;
- mapping de modèles résolu ;
- IDs/caches de ressources distantes ;
- contexte mémoire borné rendu ;
- métadonnées temporaires de session.

Cet état doit pouvoir être régénéré ou supprimé sans perte de vérité canonique.

## Choisir le runtime

Choisir le runtime selon la tâche, pas selon celui utilisé historiquement pour créer le projet.

### OpenCode

Préférer OpenCode pour :

- tester l'intégration spécifique OpenCode V1/V2 ;
- valider plugins/watchdogs OpenCode ;
- reproduire un bug runtime OpenCode ;
- utiliser l'orchestration OpenCode existante avant la parité Codex.

### Codex

Préférer Codex pour :

- implémenter/refactorer le code du dépôt ;
- utiliser les workflows de coding natifs Codex ;
- tester des stratégies subagents/modèles Codex ;
- implémenter l'adapter Codex ;
- comparer coût/qualité avec les choix runtime OpenCode.

### ChatGPT avec accès GitHub

Préférer un assistant connecté à GitHub pour :

- préparer architecture/docs/spécifications ;
- ouvrir ou mettre à jour une PR sans runtime local ;
- reviewer une PR ou un diff ;
- coordonner du travail réparti sur plusieurs dépôts ;
- transformer une discussion d'architecture en documentation durable.

Ne pas supposer que cette surface possède le même shell local ou les mêmes accès runtime que Codex/OpenCode.

## Handoff standard d'une tâche

Chaque tâche significative doit pouvoir être reprise depuis Git sans dépendre de l'historique d'un chat.

Flux recommandé :

```text
1. besoin/design durable dans docs ou issue
2. branche de tâche
3. implémentation
4. tests/checks
5. PR
6. review
7. merge
8. memory candidate si une information contextuelle durable mérite d'être conservée
```

Un handoff vers un autre runtime pointe donc vers les artefacts du dépôt :

```text
Read AGENTS.md.
Read docs/en/MULTI_RUNTIME.md.
Read docs/en/CODEX_ADAPTER.md.
Implement the next unchecked milestone on a dedicated branch.
Preserve current OpenCode behavior.
Run the relevant tests and prepare a PR.
```

C'est préférable au copier/coller d'une longue conversation.

## Contrat de handoff entre runtimes

Pour arrêter le travail dans un runtime et le reprendre ailleurs, laisser dans la branche, la PR ou un document de tâche un résumé contenant :

```text
GOAL
CURRENT STATE
FILES CHANGED
DECISIONS MADE
UNRESOLVED QUESTIONS
TESTS RUN
KNOWN FAILURES
NEXT SAFE STEP
```

Ne pas stocker de chaîne de raisonnement interne. Stocker les décisions, preuves, état d'implémentation et prochaines actions.

## Travail parallèle

OpenCode, Codex et un assistant GitHub peuvent travailler en parallèle seulement si leurs zones d'écriture ne se chevauchent pas.

Bon découpage :

```text
branche Codex A      -> refactor runtime/common
branche ChatGPT B    -> documentation/ADR
branche OpenCode C   -> correction watchdog V2
```

Découpage risqué :

```text
Codex et OpenCode modifient tous les deux scripts/generate-config sur deux branches longues
```

Préférer des branches courtes et se remettre à jour avant de toucher un hotspot partagé.

## Implémentation guidée par la documentation

Pour un changement d'architecture, la documentation doit devenir le contrat stable avant que les implémentations runtime divergent.

Ordre recommandé :

```text
discussion design
   -> PR documentation
   -> review/merge
   -> PR(s) d'implémentation
```

La PR de documentation doit définir :

- frontières de responsabilité ;
- source de vérité ;
- contrat CLI/API public ;
- invariants ;
- ordre de migration ;
- critères d'acceptation ;
- limites connues des runtimes.

Ainsi Codex, OpenCode ou un autre assistant peuvent implémenter la même cible indépendamment.

## Stratégie des modèles entre runtimes

La politique de tâche reste stable, les noms de modèles varient.

Exemple :

```text
recherche/exploration       low
implémentation              medium
orchestration               high
review finale indépendante  high
```

Chaque runtime résout les tiers indépendamment.

Ne pas copier un slug de modèle Codex dans `agents/<name>/agent.json` simplement parce qu'une session l'a utilisé avec succès.

## Workflow mémoire entre runtimes

### Lecture

Chaque runtime doit recevoir, quand l'intégration existe, le même contexte borné et spécifique au projet produit par `opencode-memory-plugin`.

Le runtime ne doit pas monter le dépôt mémoire privé simplement pour lire ce contexte.

### Proposition

Après une tâche importante, un runtime peut proposer des faits durables comme :

- une décision d'architecture ;
- une convention stable du dépôt ;
- une contrainte importante du projet ;
- une frontière de responsabilité modifiée ;
- une préférence de travail réutilisable.

Une proposition n'est pas encore une mémoire durable :

```text
runtime -> candidate -> review humaine -> promote -> push optionnel
```

### Ce qui ne doit pas devenir une mémoire

Ne pas proposer :

- erreurs de build temporaires déjà représentées dans une issue ;
- sortie brute de commandes ;
- gros diffs ;
- secrets ;
- conclusions spéculatives ;
- état temporaire d'une branche ;
- informations déjà évidentes dans les fichiers canoniques du dépôt.

## Découpage recommandé des futures PR

### PR 1 — documentation et contrats

- architecture multi-runtime ;
- contrat adapter Codex ;
- workflow cross-runtime ;
- mise à jour des index de documentation.

### PR 2 — normalisation commune

- extraire une représentation normalisée des agents ;
- golden/snapshot tests de la sortie OpenCode ;
- aucun comportement Codex requis.

### PR 3 — interface adapter + migration OpenCode

- interface commune des adapters ;
- compilateur OpenCode existant alimenté par la normalisation ;
- preuve d'absence de régression fonctionnelle.

### PR 4 — adapter Codex local

- instructions Codex générées ;
- mapping local modèles/reasoning ;
- `oc sync codex` ;
- tests dry-run/check/idempotence.

### PR 5 — surface mémoire portable

Dans `opencode-memory-plugin` quand pertinent :

- API runtime-neutre render/propose ;
- façade MCP optionnelle ;
- tests d'intégration depuis le toolkit.

### PR 6 — ressources OpenAI distantes optionnelles

- sync explicite de l'API Agents ;
- publication/versioning explicite des Skills ;
- métadonnées d'ownership ;
- dry-run distant ;
- politique de suppression sûre.

Les PR 5 et 6 ne doivent pas bloquer le support Codex local utile.

## Prompt pour Codex

Une fois la PR de documentation mergée :

```text
Read AGENTS.md and the multi-runtime documentation:
- docs/en/MULTI_RUNTIME.md
- docs/en/CODEX_ADAPTER.md
- docs/en/CROSS_RUNTIME_WORKFLOW.md

Inspect the current implementation before editing.
Implement only the next migration milestone, preserving OpenCode behavior.
Use the documented source-of-truth and compatibility rules.
Run relevant tests and prepare a PR with a clear handoff.
```

Pour une étape précise :

```text
Implement PR 2: common normalization only. Do not add Codex generation yet.
```

## Prompt pour un assistant connecté à GitHub

```text
Read the multi-runtime documentation and inspect the current repository state.
Review the implementation PR for conformance with the documented source-of-truth,
compatibility, idempotence, memory boundary, and runtime portability requirements.
Leave concrete findings or prepare a follow-up PR for documentation/test gaps.
```

## Règle de complétion

Une tâche est terminée lorsqu'un autre runtime peut comprendre ce qui a changé uniquement grâce aux artefacts Git/PR.

L'historique d'une conversation peut aider un humain, mais il ne doit jamais être nécessaire pour reconstruire l'état d'ingénierie du projet.
