# Spécification de l'adapter Codex

## But

L'adapter Codex compile les définitions canoniques du toolkit vers des artefacts, et éventuellement des ressources distantes, que Codex peut consommer.

Il doit réutiliser le même graphe normalisé qu'OpenCode. Il ne doit pas créer un catalogue d'agents parallèle propre à Codex.

## Capacités OpenAI confirmées

En septembre 2026, OpenAI documente notamment les briques suivantes utiles pour cet adapter :

- les fichiers d'instructions comme `AGENTS.md` influencent le comportement des modèles ;
- les Agents réutilisables peuvent déclarer un modèle, une configuration de reasoning et `multi_agent.max_concurrent_subagents` ;
- les Skills sont des ressources versionnées de premier niveau et peuvent être attachés à des environnements hébergés ;
- les modèles de code GPT exposent des niveaux de reasoning configurables.

Références :

- https://developers.openai.com/api/docs/guides/latest-model
- https://developers.openai.com/api/reference/typescript/resources/beta/subresources/agents/methods/create
- https://developers.openai.com/api/reference/typescript/resources/skills/methods/list
- https://developers.openai.com/api/reference/cli/resources/skills/subresources/versions/methods/create

L'implémentation doit privilégier les APIs documentées et ne pas déduire un format de configuration Codex CLI non documenté à partir d'anciens exemples.

## Première cible d'implémentation

Le premier adapter Codex utile doit être **local et réversible**.

Sorties recommandées :

```text
.generated/codex/
  AGENTS.md
  agents/
    <agent-name>.md
  skills/
    <skill-name>/...
  runtime.json
  memory-context.md        # seulement si rendu explicitement ; jamais commité avec des données privées
```

Si Codex attend un `AGENTS.md` à la racine, `oc sync codex` peut générer ou mettre à jour une section gérée dans une cible adaptée, mais le contenu canonique doit toujours venir du toolkit.

La publication distante d'Agents/Skills OpenAI est un mode ultérieur et optionnel. Elle ne doit jamais être un effet de bord d'une génération locale normale.

## Mapping depuis la définition canonique

### Identité et rôle

Sources :

```text
agents/<name>/agent.json
agents/<name>/prompt.md
```

Sortie Codex :

- nom stable ;
- description ;
- instructions composées ;
- métadonnées de parent/délégation ;
- tier de qualité ;
- tier de reasoning ;
- résumé des permissions ;
- politique mémoire ;
- intention de fiabilité.

### Tiers de modèles

Le tier canonique reste :

```text
low | medium | high
```

Codex le résout via une configuration locale, par exemple :

```bash
CODEX_MODEL_LOW=<model>
CODEX_MODEL_MEDIUM=<model>
CODEX_MODEL_HIGH=<model>
```

Surcharge optionnelle par agent :

```bash
CODEX_MODEL_ORCHESTRATOR=<model>
```

Le sens de `low`, `medium` et `high` ne doit jamais être lié définitivement à un slug de modèle.

### Tiers de reasoning

Le reasoning reste séparé de la puissance du modèle.

Politique portable :

```text
low | medium | high | xhigh
```

L'adapter peut borner une valeur non supportée, mais doit afficher ce clamp en mode verbose/dry-run.

Exemple :

```text
repo-researcher: model=low, reasoning=low
builder:         model=medium, reasoning=medium
orchestrator:    model=high, reasoning=high
review-lead:     model=high, reasoning=high
```

### Délégation

Le graphe actuel du toolkit fait foi :

```text
meta-router -> lead/orchestrator -> leaf
```

Codex ne doit pas pouvoir créer arbitrairement des rôles enfants hors du graphe validé simplement parce que le runtime supporte les subagents génériques.

Les instructions générées doivent indiquer clairement :

- quels enfants chaque lead peut lancer ;
- les leaf agents ne délèguent pas ;
- les handoffs complets doivent être réutilisés ;
- une revue indépendante peut relire les preuves primaires ;
- la limite de concurrence n'est pas un objectif de remplissage systématique.

Quand l'API Agents OpenAI est utilisée, `multi_agent.max_concurrent_subagents` devrait dériver de la configuration de fiabilité du toolkit quand c'est pertinent.

## Permissions

OpenCode et Codex n'ont pas le même modèle de tools/approvals. L'adapter mappe donc **l'intention**, pas la syntaxe.

Effets canoniques :

```text
allow
ask
deny
```

Le mapping Codex doit préserver au minimum :

- les commandes destructrices restent refusées ou soumises à approbation ;
- les chemins secrets/privés ne sont pas exposés silencieusement ;
- la délégation reste désactivée pour les leaf agents ;
- les agents capables d'écrire sont explicites ;
- reviewer/researcher restent en lecture seule sauf indication contraire dans leur définition canonique.

Si Codex ne sait pas exprimer une permission de manière déterministe, la génération doit produire un avertissement.

## Génération de AGENTS.md

`AGENTS.md` doit contenir des règles d'exploitation stables, pas un dump de mémoire projet.

Sections recommandées :

```text
# Generated runtime instructions
## Source of truth
## Agent topology
## Routing rules
## Evidence discipline
## Git safety
## Testing expectations
## Memory integration
## Runtime limitations
```

À ne pas embarquer :

- historique complet de session ;
- contenu brut du dépôt mémoire privé ;
- secrets ;
- noms de modèles temporaires lorsqu'un tier suffit ;
- données générées dont une autre source est déjà propriétaire.

## Skills

Un skill est portable lorsqu'il représente une connaissance réutilisable de domaine/workflow plutôt qu'un comportement de plugin propre à OpenCode.

L'adapter devrait classifier chaque candidat :

```text
portable
opencode-only
codex-only
unsupported
```

Une future commande explicite pourra publier les Skills Codex portables :

```bash
oc sync codex --publish-skills
```

La publication modifie un état distant : elle doit donc rester explicite.

La génération locale reste le comportement par défaut.

## Intégration mémoire

L'adapter doit utiliser `opencode-memory-plugin`, pas réimplémenter l'extraction ou le stockage.

### Lecture

Conceptuellement :

```text
projet courant
   -> résolution projet dans opencode-memory-plugin
   -> contexte borné rendu
   -> contexte/instructions Codex
```

Le runtime reçoit uniquement un rendu borné ; il n'obtient pas par défaut un accès shell direct au dépôt privé.

### Écriture

Codex peut proposer une candidate via une interface portable :

```text
session Codex
   -> memory.propose(...)
   -> quarantaine locale des candidates
   -> accept/promote explicite par un humain
   -> push explicite optionnel
```

Une session d'agent ne doit jamais commit/push implicitement une mémoire promue comme simple étape de fin de tâche.

### Direction MCP

Un petit serveur MCP autour de `opencode-memory-plugin` est une cible raisonnable s'il fournit une surface commune plus propre à OpenCode et Codex.

Tools suggérés :

```text
memory_status
memory_search
memory_render
memory_propose
memory_candidates
```

Les mutations lourdes comme promote/push doivent rester orientées CLI humaine tant qu'un futur modèle de permission ne les autorise pas explicitement.

## Intégration distante avec l'API Agents

L'API Agents OpenAI pourra devenir un backend de déploiement optionnel.

Mapping possible :

```text
agent canonique
  name           -> Agent.name
  prompt         -> Agent.instructions
  modèle concret -> Agent.model
  reasoning      -> Agent.reasoning
  concurrence    -> Agent.multi_agent.max_concurrent_subagents
  tools          -> Agent.tools
```

Ce mode doit être explicitement demandé :

```bash
oc sync codex --remote
oc sync codex --remote --dry-run
```

Contraintes :

- mapping déterministe ;
- métadonnées du toolkit sur chaque ressource distante ;
- IDs distants stockés dans un état local/généré, pas dans les définitions canoniques ;
- modification uniquement des ressources possédées par le toolkit ;
- dry-run affichant create/update/delete sans mutation ;
- suppression nécessitant un flag ou une commande explicite supplémentaire.

Les ressources API distantes ne doivent jamais être nécessaires pour utiliser Codex localement.

## Rapport des capacités runtime

`oc sync codex --verbose` devrait expliquer les écarts de portabilité.

Exemple :

```text
Codex capability report

SUPPORTED
  agent instructions
  model mapping
  reasoning mapping
  bounded subagent concurrency
  portable skills
  rendered memory context

PARTIAL
  shell permission equivalence
  step budgets

UNAVAILABLE / NOT CONFIGURED
  deterministic stall watchdog
  provider cost kill switch
```

Le vrai rapport doit être calculé depuis les capacités implémentées, pas recopié statiquement depuis cet exemple.

## Workflow Git

Le travail Codex doit suivre les mêmes règles de sécurité que le travail OpenCode :

- inspecter le status avant d'écrire ;
- utiliser/créer une branche de tâche ;
- ne jamais supprimer les changements non liés de l'utilisateur ;
- éviter par défaut reset/clean/force destructifs ;
- lancer les tests/checks pertinents ;
- résumer les fichiers modifiés ;
- préparer une PR quand demandé.

## Ordre d'implémentation recommandé

1. extraire/identifier une représentation normalisée commune ;
2. prendre des snapshots de la sortie OpenCode actuelle ;
3. faire consommer la normalisation à OpenCode sans changer sa sortie ;
4. ajouter une interface d'adapter runtime ;
5. ajouter la génération Codex locale ;
6. ajouter `oc sync`, `--dry-run` et `--check` ;
7. intégrer le rendu mémoire borné ;
8. ajouter une surface portable de proposition de candidate mémoire ;
9. ajouter éventuellement MCP ;
10. ajouter éventuellement la publication distante Agents/Skills.

Ne pas démarrer les étapes 8 à 10 avant que la génération locale soit stable et testée.

## Critères d'acceptation

Une première PR d'adapter Codex est acceptable si :

- la génération OpenCode reste inchangée ou migre intentionnellement avec tests au vert ;
- les artefacts Codex viennent des mêmes répertoires canoniques `agents/` ;
- `oc sync codex --dry-run` n'écrit rien ;
- la génération est idempotente ;
- les mappings de modèles sont configurables ;
- aucun dépôt mémoire privé n'est copié dans des fichiers générés commités ;
- au moins un lead et un leaf démontrent le bon mapping de délégation ;
- les sémantiques de permission/fiabilité non supportées sont signalées ;
- docs et tests distinguent clairement l'intégration Codex locale des ressources distantes OpenAI Agents/Skills.
