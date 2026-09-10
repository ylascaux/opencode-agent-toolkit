# Stratégie des modèles

Le toolkit est provider-agnostic. Les définitions d’agents ne dépendent pas directement de GitHub Copilot, OpenAI, Codex, LiteLLM ou d’un autre provider.

## Trois tiers de capacité

Chaque agent est rattaché à un des trois tiers stables définis dans `profiles/agent-tiers.json` :

| Tier | Modèle Copilot par défaut | Usage typique |
|---|---|---|
| `low` | `github-copilot/gpt-5.6-luna` | tâches mécaniques très bornées et à faible risque |
| `medium` | `github-copilot/gpt-5.6-terra` | ingénierie courante, collecte de preuves, documentation et analyse opérationnelle |
| `high` | `github-copilot/gpt-5.6-sol` | architecture, sécurité, arbitrage et raisonnement profond |

Le mapping par défaut privilégie la qualité plutôt qu’une réduction agressive des coûts. `mock-generator`, `secrets` et `source-discovery` sont LOW par défaut. `source-discovery` est volontairement limité à la découverte de sources candidates : il ne certifie jamais des faits métier extraits. Les tâches qui transforment les preuves en entrées utilisées ensuite pour des décisions — découverte d’architecture, extraction structurée, résolution d’entités, documentation durable, observabilité, FinOps, audit de preuves et brainstorming — utilisent au minimum MEDIUM.

Exemples :

- `mock-generator` -> LOW
- `secrets` -> LOW
- `source-discovery` -> LOW
- `structured-extractor` -> MEDIUM
- `entity-resolver` -> MEDIUM
- `project-scanner` -> MEDIUM
- `docs-writer` -> MEDIUM
- `builder` -> MEDIUM
- `evidence-auditor` -> MEDIUM
- `platform-architect` -> HIGH
- `appsec` -> HIGH

Le mapping agent → tier ne dépend pas du provider concret. Un agent conserve le même tier de capacité lors d’un changement de profil provider.

## Pourquoi la plupart des agents producteurs de preuves ne sont pas LOW

Certains agents qui semblent simples produisent en réalité des informations que les agents suivants utilisent comme preuves. Une sortie faible à ce niveau peut se propager dans tout le raisonnement en aval.

Par exemple, `project-scanner` découvre les composants, interfaces, infrastructures, data stores et relations de preuves utilisées ensuite par les agents d’architecture. `structured-extractor` transforme des preuves en données candidates structurées, tandis que `entity-resolver` peut influencer les décisions de déduplication en aval. `docs-writer` conserve les décisions, hypothèses, migrations et rollback dans les artefacts durables. `observability` et `finops` réalisent de vrais compromis opérationnels au lieu de simplement extraire des valeurs. Ils sont donc MEDIUM par défaut.

`source-discovery` est l’exception étroite : sa sortie LOW est uniquement une liste de sources candidates et ne doit jamais être traitée comme une donnée métier de confiance. L’extraction ou les décisions d’identité passent en MEDIUM, puis les incertitudes persistantes à risque élevé sont escaladées plus haut.

`evidence-auditor` est MEDIUM car son travail normal est une vérification structurée. Un désaccord matériel ou une incertitude à risque élevé doit être escaladé vers des agents HIGH comme `arbiter` ou `deep-reasoner`, plutôt que de rendre chaque audit HIGH par défaut.

## Profils

Les modèles concrets sont définis dans `profiles/*.env.example`.

```bash
just profiles
just profile copilot
just profile codex
just models
```

Le profil de travail par défaut est `copilot`.

Le provider GitHub Copilot d’OpenCode est `github-copilot`. Il faut vérifier les modèles réellement exposés par le compte :

```bash
opencode models github-copilot
```

Si les IDs disponibles diffèrent, il suffit d’éditer `profiles/copilot.env.example` ; aucun agent ni règle de routage n’a besoin d’être modifié.

## Usage personnel / Codex

`profiles/codex.env.example` fournit un profil personnel prêt à être adapté.

```bash
just profile codex
```

On peut utiliser un seul modèle Codex/OpenAI pour les trois tiers, ou attribuer des modèles différents à `MODEL_LOW`, `MODEL_MEDIUM` et `MODEL_HIGH`.

## Overrides par agent

Les overrides persistants doivent être placés dans `.env.local` :

```bash
MODEL_BUILDER=openai/gpt-5.3-codex
MODEL_REVIEWER=github-copilot/gpt-5.6-sol
```

`.env.local` est chargé après `.env` et un changement de profil ne le modifie jamais.

Ordre de résolution :

```text
MODEL_<AGENT> override
        ↓
tier de l’agent dans profiles/agent-tiers.json
        ↓
MODEL_LOW / MODEL_MEDIUM / MODEL_HIGH du profil actif
```

## Pourquoi trois tiers plutôt que 40 modèles fixes ?

Les tiers gardent une politique coût/qualité stable même quand les providers changent. Il suffit de modifier trois valeurs pour migrer les 40 agents sans toucher aux configs OpenCode générées ni au manifest des agents.

`meta-router` garde le travail ordinaire sur des chemins MEDIUM et utilise les agents HIGH pour les sujets à risque élevé, faible confiance, sécurité sensible ou architecture complexe. LOW est volontairement réservé aux tâches étroites dont les erreurs ont peu d’impact en aval ou, comme `source-discovery`, dont la sortie ne peut pas être considérée comme une donnée de confiance par les étapes suivantes.

## LiteLLM

LiteLLM reste optionnel et ne fait pas partie de l’installation par défaut. `just configure-litellm` reste disponible pour un futur usage gateway. Les credentials utilisés pour la découverte ne sont pas persistés par le configurateur.
