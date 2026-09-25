# V2 — ACP runners

## État

**Implémenté pour OpenCode.**

OpenCode reste le runtime principal et fournit son serveur ACP natif :

```bash
opencode acp
```

Le toolkit ne réimplémente pas le serveur OpenCode. Il implémente le **client/manager ACP** qui permet à un agent parent de lancer des jobs enfants via ACP.

Références :

- https://opencode.ai/v2/docs/cli/acp/
- https://agentclientprotocol.com/protocol/initialization
- https://agentclientprotocol.com/protocol/session-setup
- https://agentclientprotocol.com/protocol/prompt-turn
- https://agentclientprotocol.com/protocol/tool-calls
- https://github.com/TencentCloud/Octop/blob/main/docs/acp.md

## Architecture

```text
parent OpenCode
    │
    └── MCP oat-acp
          │
          └── acp_runner
                │
                └── bounded job pool
                      ├── opencode acp child #1
                      ├── opencode acp child #2
                      ├── opencode acp child #3
                      └── opencode acp child #4
```

Le nombre de jobs est contrôlé par :

```bash
OAT_ACP_MAX_PARALLEL=4
OAT_ACP_TIMEOUT_SECONDS=600
```

## Registre de runners

`config/acp-runners.json` contient uniquement des commandes approuvées.

Runner par défaut :

```text
opencode -> opencode acp
```

La commande peut être remplacée par `OPENCODE_BIN`.

Inspection humaine :

```bash
oc runner list
oc runner doctor
oc runner command opencode
```

`oc runner exec opencode` expose directement le flux ACP stdio, principalement pour diagnostic/intégration.

## Outil agent : acp_runner

Le MCP `oat-acp` expose un outil unique avec les actions :

```text
list
start
message
respond
status
close
```

### start

Crée un processus ACP + une session. Si `message` est fourni, le prompt est envoyé au pool et l'appel retourne immédiatement :

```json
{
  "status": "running",
  "session_id": "..."
}
```

### status

Le parent poll `status`. Il obtient :

- `running` pendant le travail ;
- le résultat `completed` à la fin ;
- `permission_required` lorsque l'enfant demande une autorisation ;
- `failed` en cas d'erreur.

Les chunks `session/update` sont agrégés de façon bornée et les derniers updates restent disponibles pour diagnostic.

### message

Continue une session existante. Comme `start`, l'opération est mise dans le pool et rend immédiatement la main.

### respond

Reprend un prompt suspendu sur `session/request_permission` avec **l'option exacte** fournie par ACP.

Le parent ne doit jamais inventer une option : les instructions des agents imposent de demander/consommer une autorisation explicite correspondant à la politique parent.

### close

Ferme la session et termine le processus. Un prompt actif est annulé avant terminaison.

## ACP v1 pris en charge

Le client toolkit implémente :

1. `initialize` avec `protocolVersion: 1` ;
2. `session/new` ;
3. `session/prompt` ;
4. `session/update` ;
5. `session/request_permission` ;
6. `session/cancel` ;
7. `session/close` lorsque la capability est annoncée.

Chaque ligne stdio est un message JSON-RPC indépendant.

## Parallélisme

`start/message/respond` ne bloquent pas le serveur MCP : le travail se fait dans un `ThreadPoolExecutor` borné.

Ce choix évite le problème d'un serveur MCP stdio séquentiel qui annulerait en pratique tout bénéfice du multi-agent.

Le pool est local au processus `oat-acp` : aucun daemon, broker ou base de jobs n'est ajouté.

## Parent/child

La topologie reste contrôlée :

```text
parent
  └── child ACP
```

Le child ne reçoit pas `oat-acp`, ce qui bloque la récursion ACP non bornée.

Le catalogue natif OpenCode reste disponible au parent pour les petits handoffs. Les prompts des leads indiquent :

- délégation native pour un spécialiste court ;
- ACP pour travail indépendant/long, background, ou runtime alternatif ;
- toujours fermer les sessions terminées.

## Isolation

Un enfant ACP :

- doit utiliser un runner `trusted=true` ;
- travaille dans le workspace parent ou un sous-répertoire ;
- ne peut pas choisir une commande de runner arbitraire ;
- ne reçoit pas `oat-acp` ;
- ne reçoit pas `oat-memory` ;
- ne reçoit pas le DSN PostgreSQL ;
- a la capture mémoire automatique désactivée.

Cela empêche un enfant de recréer une chaîne de délégation autonome et évite de dupliquer les captures mémoire.

## Permissions

Une demande ACP `session/request_permission` est convertie en état `permission_required` avec les options d'origine.

Le parent peut ensuite appeler `respond` avec un `option_id` exact.

Les permissions ne sont jamais choisies automatiquement par le session manager.

## Limites

La V2 ne persiste pas les jobs ACP après le décès du processus parent : ils sont volontairement éphémères.

C'est cohérent avec l'objectif de maintenance minimale. Une queue persistante ne sera ajoutée que si un besoin réel apparaît.

## Ajouter un autre runner

Le registre permet d'ajouter ultérieurement Codex, Claude Code ou un autre agent ACP sans modifier l'orchestrateur :

```json
{
  "runners": {
    "opencode": {
      "command": "opencode",
      "args": ["acp"],
      "enabled": true,
      "trusted": true
    }
  }
}
```

Un nouveau runner reste désactivable et doit passer les mêmes tests de protocole/permissions/isolation.
