# Worker de recherche externe

Le worker de recherche externe permet à une machine de confiance de récupérer des jobs de recherche neutres depuis une application consommatrice et de les exécuter via OpenCode Agent Toolkit local.

Il reste volontairement générique. L'application consommatrice possède l'ordonnancement (par exemple n8n), la persistance des jobs, les schémas métier, les données canoniques, l'ingestion des preuves, le scoring et la publication. Le toolkit possède uniquement l'exécution locale de la recherche, le routage agents/modèles et les retries provider/outils.

## Frontière

```text
application consommatrice
        |
        | HTTPS claim/result
        v
machine worker de confiance
        |
        v
research-runner
        |
        +--> source-discovery
        +--> structured-extractor
        +--> entity-resolver si nécessaire
        +--> evidence-auditor si nécessaire
        +--> deep-reasoner seulement si la politique locale l'autorise
        |
        v
résultat candidat structuré
```

L'application peut définir **quelles** informations sont recherchées. Elle ne peut pas choisir à distance un modèle, provider, agent, prompt, commande shell, callback, outil, chemin local ou configuration OpenCode. Ces champs de contrôle sont refusés récursivement avant toute exécution.

L'agent `research-runner` est volontairement restreint : lecture de fichiers locaux, édition, shell, skills et accès aux répertoires externes sont interdits. Le contenu du job et des sources est une donnée non fiable, jamais une instruction.

## Configuration

Place les secrets et paramètres propres au site dans `.env.local`, ignoré par Git :

```bash
OAT_RESEARCH_API_URL=https://research.example.com
OAT_RESEARCH_API_TOKEN=replace-me
OAT_RESEARCH_WORKER_ID=my-mac
OAT_RESEARCH_JOB_TYPES=SPECIFICATIONS,SUPPORT_LIFECYCLE,SECURITY_LIFECYCLE,REPAIRABILITY,RELIABILITY_RESEARCH,IOT_CAPABILITIES,COMPATIBILITY,MARKET_VALUE,SOURCE_REFRESH,ENTITY_RECONCILIATION
```

Politiques locales utiles :

```bash
OAT_RESEARCH_MAX_PARALLEL=1
OAT_RESEARCH_MAX_ATTEMPTS=2
OAT_RESEARCH_MAX_TIER=high
OAT_RESEARCH_POLL_MIN_SECONDS=5
OAT_RESEARCH_POLL_MAX_SECONDS=30
OAT_RESEARCH_EXECUTION_TIMEOUT_SECONDS=900
```

Ces valeurs sont locales. Un ResearchJob distant ne peut pas les écraser.

En production, l'API doit utiliser HTTPS. HTTP n'est accepté que pour `localhost`, `127.0.0.1` et `::1` en développement. Le Bearer token est envoyé uniquement dans l'en-tête `Authorization` et ne doit jamais être passé comme argument CLI.

## Lancement

Avec le runtime Docker par défaut :

```bash
bash scripts/research-worker --once
bash scripts/research-worker
```

Le launcher démarre/réutilise le serveur OpenCode V2 persistant et exécute le worker dans ce conteneur. L'hôte n'a donc besoin que de Docker, pas d'une installation Python/OpenCode séparée.

`--once` récupère et traite au maximum un batch selon la limite locale de parallélisme. Sans cette option, le worker poll en continu avec un backoff borné lorsqu'il n'y a pas de travail ou lorsque l'API est temporairement indisponible.

## Contrat de claim

Le worker envoie son identité, sa version, les types de jobs neutres supportés et sa limite locale de concurrence. Un job réclamé ressemble par exemple à :

```json
{
  "job_id": "job-123",
  "job_type": "SUPPORT_LIFECYCLE",
  "subject": {
    "type": "product",
    "id": "product-123",
    "slug": "example-device"
  },
  "requested_fields": ["security_support_end"],
  "requirements": {
    "preferred_source_types": ["MANUFACTURER"]
  },
  "schema_version": "1",
  "result_schema": {
    "type": "object"
  },
  "lease": {
    "generation": 4,
    "expires_at": "2026-09-11T12:00:00Z"
  }
}
```

Aucune information de modèle/provider/agent ne doit apparaître dans ce contrat.

## Exécution et escalade

Le worker convertit le job externe neutre vers l'enveloppe générique `Research Job` du toolkit puis lance `research-runner`. Les profils locaux LOW/MEDIUM/HIGH restent autoritaires. Le toolkit peut utiliser découverte de sources, extraction, audit de preuves et deep reasoning en fonction de la qualité des preuves et du tier maximal configuré localement.

La réponse machine finale est extraite via un marqueur explicite et validée avec l'un des statuts :

- `SUCCESS`
- `PARTIAL`
- `NO_DATA`
- `CONFLICT`
- `FAILED`

avec une confiance `HIGH`, `MEDIUM` ou `LOW`, des données structurées, des preuves et des warnings.

Même valide pour le toolkit, cette sortie reste une **preuve candidate**. L'application consommatrice doit valider déterministiquement son payload métier avant persistance ou publication.

## Responsabilité des échecs

Les retries liés au toolkit/provider restent locaux au toolkit. Si l'exécution locale elle-même échoue ou dépasse le timeout, le worker ne fabrique pas un résultat FAILED uniquement pour acquitter le job. Il laisse expirer le lease afin que la queue de l'application consommatrice applique sa propre politique worker-crash/retry/dead-letter.

Cela évite que deux systèmes de retry indépendants acquittent incorrectement le même échec.

## Propriétés de sécurité

- connexion sortante depuis le worker uniquement ; aucun serveur entrant sur le Mac n'est requis ;
- HTTPS obligatoire hors développement loopback ;
- authentification Bearer fournie par la configuration locale ;
- aucun callback distant arbitraire ;
- aucun contrôle distant de shell/commande/chemin/modèle/agent/provider ;
- tailles de requêtes/réponses/résultats bornées ;
- contenu externe et job traités comme données non fiables ;
- `research-runner` ne peut ni lire/éditer les fichiers locaux ni utiliser le shell ;
- l'application externe ne reçoit jamais les credentials des modèles et n'a pas besoin de connaître les providers.

## Tests

Les tests de contrat et de sécurité sont dans `tests/test_research_worker.py` et passent dans la suite Python normale :

```bash
python3 -m unittest discover -s tests -v
```

Aucune API externe réelle ni aucun appel LLM réel n'est nécessaire en CI.
