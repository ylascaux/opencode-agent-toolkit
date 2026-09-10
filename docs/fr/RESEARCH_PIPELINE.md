# Pipeline de recherche structurée

Ce toolkit fournit des agents OpenCode réutilisables et des enveloppes lisibles par machine pour de la recherche externe fondée sur des preuves. Il ne possède volontairement **ni** les schémas métier, **ni** la persistance, **ni** le scoring, **ni** le dataset canonique, **ni** la configuration du moteur de workflow.

## Frontière

L’application consommatrice possède :

- la planification et l’orchestration des workflows (par exemple n8n) ;
- la persistance des jobs, leur claim, l’idempotence et le stockage des résultats ;
- les schémas métier et leur validation déterministe ;
- les règles canoniques de résolution/déduplication d’entités ;
- le scoring métier, les règles d’approbation et la publication.

Le toolkit possède :

- `source-discovery` : trouver un petit ensemble de sources candidates ;
- `structured-extractor` : extraire des données candidates structurées depuis les preuves fournies ;
- `entity-resolver` : évaluer les conflits d’identité sans modifier les données canoniques ;
- `evidence-auditor` : vérifier indépendamment les sorties de confiance MEDIUM ou partiellement vérifiées ;
- `deep-reasoner` : traiter les cas à risque HIGH, les conflits matériels ou une confiance LOW persistante ;
- les garde-fous runtime existants sur les retries, le parallélisme, les steps et les coûts.

Un moteur de workflow comme n8n appartient au dépôt de l’application consommatrice. Aucun workflow n8n, credential, base de données, queue ou règle métier spécifique ne doit être ajouté à ce toolkit.

## Flux recommandé

```text
workflow / scheduler externe
        |
        v
enveloppe Research Job
        |
        v
orchestrator OpenCode
        |
        +--> source-discovery       (LOW convient à une découverte bornée)
        |
        +--> structured-extractor   (MEDIUM)
        |
        v
validation déterministe du schéma côté appelant
        |
        +--> erreur de validation -> un retry ciblé avec les erreurs exactes
        |
        +--> ambiguïté d’identité -> entity-resolver (MEDIUM)
        |
        +--> confiance MEDIUM / preuves partielles -> evidence-auditor
        |
        +--> risque HIGH, conflit matériel ou confiance LOW persistante
        |       -> deep-reasoner (HIGH)
        |
        v
enveloppe Research Result
        |
        v
checks déterministes / persistance / publication côté appelant
```

Le chemin LOW -> MEDIUM -> HIGH est une échelle d’escalade, pas une chaîne obligatoire. Il faut démarrer avec l’agent le moins coûteux suffisant et n’escalader que lorsque les preuves, les erreurs de validation, le risque ou l’incertitude le justifient.

## Contrats

`contracts/research-job.schema.json` est l’enveloppe d’entrée. `target_schema` est optionnel et appartient à l’appelant : le toolkit peut le consommer mais n’en devient jamais la source de vérité.

`contracts/research-result.schema.json` est l’enveloppe de sortie. Son champ `data` reste volontairement générique. Un Research Result valide syntaxiquement ne prouve **pas** que `data` respecte le schéma métier de l’application.

L’appelant doit valider :

1. l’enveloppe générique du résultat ;
2. le payload métier avec son propre schéma et ses règles déterministes.

## Confiance et escalade

- **Confiance HIGH** : les affirmations importantes disposent de preuves directes et suffisantes. On continue vers les checks déterministes de l’appelant.
- **Confiance MEDIUM** : les preuves sont solides mais indirectes, incomplètes ou nécessitent un contrôle indépendant. Exécuter `evidence-auditor` avant une acceptation automatique.
- **Confiance LOW** : ambiguïté, preuve manquante ou conflit matériel non résolu. Ne jamais auto-accepter. Retry uniquement si un manque précis de validation/preuve peut être corrigé ; sinon escalader ou retourner un état bloqué.

Le risque et la confiance sont distincts. Une décision à risque HIGH peut nécessiter `deep-reasoner` même lorsque les preuves paraissent solides.

## Discipline des retries

Ne jamais répéter aveuglément le même prompt. Un retry doit contenir une information nouvelle : erreurs exactes de validation de schéma, source inaccessible, liste de champs manquants ou conflit de preuves précis. Respecter `max_attempts`, les budgets runtime du toolkit et la limite de parallélisme configurée.

Les erreurs transitoires de provider/outils sont gérées par la couche de fiabilité du toolkit. Les erreurs de validation métier appartiennent à l’appelant et doivent être renvoyées comme entrée structurée de correction.

## Automatisation externe

Pour un job structuré connu, un worker externe peut invoquer `orchestrator` en non-interactif et demander une réponse JSON `Research Result`. Le workflow externe doit considérer OpenCode comme une dépendance d’exécution, pas comme la base de données ni comme la source de vérité métier.

La frontière reste remplaçable : n8n pourra être remplacé sans changer les agents de recherche, et les profils de modèles/providers pourront évoluer sans changer le modèle de domaine de l’application consommatrice.
