# Interface Web OpenCode

Le launcher du toolkit supporte directement `web` et `serve`. Il n'existe pas de configuration OpenCode séparée pour le Web : `oc2 web` utilise la même configuration V2 générée, les mêmes agents, plugins, modèles et permissions que le TUI.

## Démarrage rapide

Depuis le projet sur lequel OpenCode doit travailler :

```bash
cd ~/Projects/my-project
oc2 web
```

Pour fixer le port :

```bash
oc2 web --port 4096
```

Le launcher sélectionne automatiquement `opencode2` et exporte `OPENCODE_CONFIG` vers `opencode.v2.jsonc`.

Depuis le repository du toolkit, les raccourcis équivalents sont :

```bash
just web-v2 --port 4096
just serve-v2 --port 4096
```

`just web` et `just serve` utilisent la version OpenCode active définie par le toolkit.

## Authentification

OpenCode protège `web` et `serve` avec une authentification HTTP Basic lorsque `OPENCODE_SERVER_PASSWORD` est défini. Le nom d'utilisateur par défaut est `opencode`; il peut être remplacé avec `OPENCODE_SERVER_USERNAME`.

Définis les variables dans ton shell avant de lancer le serveur :

```bash
export OPENCODE_SERVER_USERNAME="yoann"
export OPENCODE_SERVER_PASSWORD="change-me"

oc2 web --port 4096
```

Le launcher transmet naturellement ces variables au processus OpenCode. Il ne les copie pas dans la configuration générée et ne les écrit pas dans le repository.

Évite de committer un mot de passe dans `.env`, `.env.local`, `opencode.v2.jsonc` ou tout autre fichier versionné. Pour un secret durable, utilise de préférence un gestionnaire de secrets ou le trousseau système, puis exporte la valeur au démarrage du shell.

## Accès local uniquement

Pour une utilisation uniquement sur le Mac :

```bash
oc2 web --hostname 127.0.0.1 --port 4096
```

Puis ouvre :

```text
http://127.0.0.1:4096
```

Même avec une écoute locale, garder `OPENCODE_SERVER_PASSWORD` défini est raisonnable si tu veux un comportement identique entre tes différents modes d'exécution.

## Accès depuis le réseau local

Pour rendre l'interface accessible depuis une autre machine :

```bash
export OPENCODE_SERVER_USERNAME="yoann"
export OPENCODE_SERVER_PASSWORD="change-me"

oc2 web --hostname 0.0.0.0 --port 4096
```

Ne publie pas un serveur OpenCode sur `0.0.0.0` sans mot de passe.

## Web UI et TUI en même temps

Lance d'abord le serveur Web :

```bash
oc2 web --port 4096
```

Puis, dans un autre terminal :

```bash
opencode2 attach http://127.0.0.1:4096
```

Si l'authentification est activée, `attach` réutilise `OPENCODE_SERVER_USERNAME` et `OPENCODE_SERVER_PASSWORD` présents dans l'environnement.

Les deux clients utilisent alors le même serveur et les mêmes sessions.

## Serveur headless

Pour exposer uniquement l'API OpenCode, sans ouvrir l'interface Web :

```bash
oc2 serve --hostname 127.0.0.1 --port 4096
```

Le endpoint OpenAPI est disponible sous `/doc` sur le serveur.

## Vérification

Après modification du toolkit :

```bash
just test
just web-v2 --help
```

Les tests du launcher vérifient que `oc2 web` sélectionne bien OpenCode V2, utilise `opencode.v2.jsonc`, conserve les arguments Web et transmet les variables d'authentification sans afficher le mot de passe.
