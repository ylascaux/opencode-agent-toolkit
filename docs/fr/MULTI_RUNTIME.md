# Architecture multi-runtime

## Objectif

`opencode-agent-toolkit` doit évoluer d'un toolkit centré sur OpenCode vers un **plan de contrôle d'agents indépendant du runtime**.

Le toolkit reste la source de vérité pour les rôles, prompts, permissions, niveaux de modèles, topologie de délégation, intentions de fiabilité et intégration mémoire. Les adapters compilent ensuite cette source vers OpenCode, Codex puis éventuellement d'autres runtimes.

```text
                         opencode-agent-toolkit
                         SOURCE DE VÉRITÉ
                                 |
                 +---------------+---------------+
                 |                               |
                 v                               v
          adapter OpenCode                  adapter Codex
                 |                               |
                 v                               v
        config OpenCode générée          artefacts Codex générés

                                 |
                                 v
                     opencode-memory-plugin
                                 |
                                 v
                        dépôt mémoire privé
```

La synchronisation est volontairement à sens unique :

```text
Toolkit -> artefacts runtime
```

Les fichiers spécifiques à un runtime ne doivent jamais devenir une seconde source de vérité éditable.

## Sources de vérité existantes

Le dépôt possède déjà les bonnes primitives :

- `agents/<nom>/agent.json` : métadonnées d'agent et extensions éventuelles spécifiques au runtime ;
- `agents/<nom>/prompt.md` : comportement de l'agent ;
- `agents/<nom>/permissions.json` : surcharges de permissions ;
- `agents/_defaults/` : valeurs communes héritées ;
- tiers `low`, `medium`, `high` plutôt que modèles fournisseurs codés en dur ;
- génération et validation déterministes ;
- graphe parent/enfant peu profond ;
- mémoire externalisée dans `opencode-memory-plugin`.

Le chantier multi-runtime doit **formaliser et réutiliser ces primitives**, pas créer un nouveau manifest concurrent.

## Principes de conception

### 1. Le modèle commun d'abord

Une définition d'agent décrit une intention :

```json
{
  "description": "Inspecter un dépôt et retourner des constats appuyés par des preuves.",
  "mode": "subagent",
  "tier": "low",
  "steps": 10,
  "parents": ["orchestrator"]
}
```

Elle ne doit pas dépendre d'un slug de modèle OpenCode/OpenAI.

Quand une option est réellement propre à un runtime, elle peut être placée sous un namespace :

```json
{
  "opencode": {},
  "codex": {}
}
```

Le comportement commun doit rester hors de ces extensions.

### 2. Les tiers de capacité restent stables

Le contrat portable est :

```text
low
medium
high
```

Le choix du modèle concret appartient au profil local ou à l'adapter.

```text
                    profil OpenCode        profil Codex
low                 modèle économique      modèle code rapide/économique
medium              modèle équilibré       modèle code équilibré
high                meilleur modèle        meilleur modèle code
```

Les noms de modèles évoluent plus vite que le graphe d'agents : ils sont donc de la configuration, pas de l'architecture.

### 3. Les sémantiques de fiabilité sont portables, leur implémentation ne l'est pas forcément

Le toolkit définit l'intention :

- profondeur maximale de délégation ;
- nombre maximal d'enfants parallèles ;
- retries bornés ;
- budget d'étapes/tâches ;
- gestion des stalls ;
- pas d'opérations Git destructrices par défaut ;
- revue indépendante quand nécessaire ;
- le producteur ne certifie pas seul son propre travail ;
- un handoff complet doit être réutilisé plutôt que recalculé sans raison.

Chaque adapter peut appliquer ces règles différemment selon les capacités natives du runtime.

Si un runtime ne sait pas garantir une règle de manière déterministe, l'adapter doit l'indiquer explicitement.

### 4. La mémoire est une frontière de service

La mémoire n'appartient ni à OpenCode ni à Codex.

```text
OpenCode ----+
             |
Codex -------+---- opencode-memory-plugin ---- dépôt mémoire Git privé
             |
autre -------+
```

Le toolkit configure l'accès. L'extraction, les candidates, la curation, le retrieval, la persistance Git et la promotion restent dans `opencode-memory-plugin`.

Interface portable cible :

```text
memory.search
memory.render
memory.propose
memory.list_candidates
memory.accept
memory.promote
```

Les agents peuvent proposer des candidates. La promotion durable reste explicite et révisable par un humain.

### 5. Les artefacts générés sont jetables

Les sorties spécifiques aux runtimes doivent pouvoir être régénérées à partir des sources du toolkit.

Un checkout propre + un profil runtime local doivent suffire.

Les sorties générées devraient porter un en-tête similaire à :

```text
GENERATED FILE - DO NOT EDIT
Source: opencode-agent-toolkit
Regenerate with: oc sync <runtime>
```

## Architecture cible du dépôt

La structure exacte pourra évoluer, mais la séparation logique cible est :

```text
agents/                         # sources canoniques des agents
contracts/                      # contrats portables
runtime/
  common/                       # normalisation + validation commune
  opencode/                     # compiler/adapter OpenCode
  codex/                        # compiler/adapter Codex
scripts/
  ...
.generated/
  opencode/
  codex/
```

Il ne faut pas déplacer des fichiers uniquement pour coller à ce dessin si la séparation peut être obtenue avec moins de churn.

## Modèle normalisé d'un agent

Le compilateur commun doit produire une représentation interne unique avant d'appeler un adapter.

Forme conceptuelle :

```yaml
name: repo-researcher
description: Inspect repository evidence
mode: subagent
parents:
  - orchestrator
model:
  tier: low
  override_env: MODEL_REPO_RESEARCHER
reasoning:
  tier: low
permissions:
  read: allow
  edit: deny
  shell: ask
  delegate: deny
memory:
  read: true
  propose: true
reliability:
  steps: 10
```

Ce format est un contrat interne, pas forcément un nouveau format YAML exposé aux utilisateurs.

## CLI de synchronisation

UX cible :

```bash
oc sync opencode
oc sync codex
oc sync all
```

Options utiles :

```bash
oc sync codex --dry-run
oc sync codex --check
oc sync codex --verbose
```

Sémantique :

- `--dry-run` : rend/diff sans écrire ;
- `--check` : retourne un code non nul si les artefacts sont obsolètes ;
- mode normal : met à jour les artefacts de manière idempotente ;
- deux runs sans changement doivent produire des octets identiques.

Exemple :

```text
Codex synchronization

agents:          41 discovered
skills:          6 mapped
memory:          configured
AGENTS.md:       update required
runtime config:  update required

model policy:
  orchestrator   high
  implementer    medium
  researcher     low
  reviewer       high
```

Les nombres doivent être découverts dynamiquement, jamais codés en dur.

## Précédence de configuration

L'intention portable est résolue avant la configuration runtime :

```text
surcharge agent
    -> mapping tier/profil
    -> surcharge locale runtime
    -> valeur par défaut runtime
```

Les secrets et préférences personnelles de modèles restent hors des fichiers générés commités.

## Stratégie de compatibilité

Migration incrémentale obligatoire :

1. préserver le comportement OpenCode actuel ;
2. extraire une représentation normalisée depuis le générateur existant ;
3. faire consommer cette représentation par la génération OpenCode ;
4. prouver l'absence de régression avec les tests ;
5. ajouter la génération Codex depuis la même représentation ;
6. seulement ensuite simplifier les anciens chemins dupliqués.

Une grosse réécriture qui implémente Codex puis reconstruit OpenCode ensuite est hors scope.

## Tests minimum

Le support multi-runtime doit couvrir :

- découverte et normalisation de tous les agents ;
- validation du graphe ;
- résolution des tiers de modèles ;
- sortie adapter OpenCode ;
- sortie adapter Codex ;
- isolation des surcharges spécifiques à chaque runtime ;
- `--dry-run` sans écriture ;
- `--check` détectant les artefacts obsolètes ;
- génération idempotente ;
- ordre stable ;
- intégration mémoire rendue ;
- échec avant lancement d'un modèle si la config runtime est invalide ;
- impossibilité qu'un fichier généré devienne silencieusement une source d'entrée.

Les golden/snapshot tests sont adaptés aux artefacts déterministes.

## Hors scope initial

Le premier support multi-runtime n'impose pas :

- la parité de tous les hooks OpenCode ;
- le retour de l'implémentation mémoire dans ce dépôt ;
- le masquage des différences entre runtimes ;
- la promotion automatique des memory candidates ;
- le codage en dur des noms de modèles Codex dans les agents ;
- la publication de ressources OpenAI distantes pendant une génération locale normale.

## Définition de terminé

L'architecture multi-runtime est établie lorsque :

1. les workflows OpenCode existants fonctionnent toujours ;
2. un seul graphe normalisé alimente OpenCode et Codex ;
3. `oc sync codex --dry-run` explique ce qui serait généré ;
4. Codex consomme les instructions/skills/config sans duplication des sources ;
5. la mémoire peut être rendue pour Codex sans exposer le dépôt privé ;
6. la documentation indique clairement les garanties de fiabilité réellement déterministes pour chaque runtime.
