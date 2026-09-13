# OpenCode Agent Toolkit — native workflow

Agents et skills partagés pour OpenCode V1/V2 et Codex, sans Docker pour `oc` et
`oc2`. Le contrôle reste court : `meta-router -> lead/orchestrator -> specialist`.
La synchronisation Codex et la mémoire externe sont conservées.

## Installation locale

Prérequis : Bash, Python 3.11+, les exécutables natifs `opencode` / `opencode2`,
et `just` pour les raccourcis. Node/npm ne sont nécessaires que pour installer
les CLI via npm, développer les anciens plugins ou activer la mémoire externe.
Le toolkit n'installe plus de runtime Docker, Nix ou environnement Python à votre insu.

Si les CLI ne sont pas déjà installées, une installation npm dans votre compte
utilisateur est possible (ne remplacez pas une version existante sans raison) :

```bash
npm install --global --prefix "$HOME/.local" opencode-ai
npm install --global --prefix "$HOME/.local" @opencode/cli@0.0.0-beta-19507
export PATH="$HOME/.local/bin:$PATH"
```

La version V2 est volontairement explicite : ne suivez pas automatiquement le canal
beta sur une machine de travail. `OPENCODE_BIN` permet d'utiliser un autre chemin
vers un véritable binaire natif, jamais vers `oc` ou `oc2` eux-mêmes.

Dans le dépôt du toolkit :

```bash
just install
just doctor
```

`just install` crée `.env` si nécessaire, génère les configurations et installe les
deux liens utilisateur. Il préserve `.env` / `.env.local`, les modèles et la mémoire.
Il ne lance ni tests, ni daemon, ni installation globale de dépendances.

Depuis le projet à modifier :

```bash
oc auth login
oc2 auth login
oc
oc2
oc2 run "Corrige le problème et ajoute un test"
```

Le répertoire courant, le HOME, les credentials natifs, les arguments et les codes
de sortie sont préservés. L'authentification et l'aide ne dépendent pas de la
génération des agents, des modèles ou du plugin mémoire. V2 utilise une session
locale `--standalone` par défaut, sans serveur persistant géré par le toolkit.
Un serveur explicite reste possible avec `oc2 serve --hostname 127.0.0.1 --port 4096`
ou `oc2 --server http://127.0.0.1:4096`. Ne l'exposez pas publiquement sans
l'authentification native OpenCode.

## Une surface `just` courte

`install`, `profile`, `config`, `doctor`, `oc`, `oc2`, `sync`, `codex`, `memory`,
`test`, `check`. Les sous-commandes passent leurs arguments tels quels.

```bash
just profile copilot
just memory status
just memory candidates
just sync codex
just check
```

Les opérations avancées historiques restent accessibles explicitement dans
`scripts/`, mais ne font plus partie du démarrage normal. Le scanner/API et leurs
dépendances sont optionnels. `test` / `check` sont réservés aux contributeurs :
les tests historiques de plugins demandent Node et `npm ci` dans ce dépôt.

## Agents sans supervision intrusive

Les configurations utilisées par `oc` / `oc2` n'activent plus la sandbox, les
plugins de watchdog ou de validation de plan, ni les anciens plafonds de 8/16
étapes. Un orchestrateur silencieux n'est pas tué. La limite de parallélisme
`MAX_PARALLEL_SUBAGENTS` reste une instruction aux agents, pas une garantie
apportée par un superviseur externe.

Le routage, les skills, les permissions explicites de chaque rôle et la revue
indépendante sont conservés. Les commandes locales habituelles et Git distant
ne nécessitent plus le contournement manuel de l'ancienne sandbox. Les protections
contre la lecture de clés privées, les actions destructrices et l'écrasement des
fichiers Codex personnels restent en place. Ce mode natif n'est **pas une isolation** :
les outils s'exécutent avec les accès de votre compte et les permissions configurées.

Les sources canoniques restent `agents/` et `skills/`. Le renderer natif produit
les copies adaptées à OpenCode sans modifier les sources consommées par Codex.
Le renderer historique reste disponible pour les intégrations existantes ;
`oc sync opencode` utilise encore ce format historique. Un lancement `oc`/`oc2`
régénère toujours le format natif.

## Codex : synchronisation conservée

```bash
oc sync codex
oc sync codex --dry-run
oc sync codex --check

cd /chemin/vers/le-projet
oc codex install
oc codex doctor
oc codex install --with-memory
oc codex uninstall
```

Ces commandes restent utilisables sans Docker, sans binaire OpenCode et sans
`.env` du toolkit. Les fichiers non gérés ou modifiés manuellement restent protégés
par le manifest d'ownership. Les adapters Codex et le service MCP ne sont pas remplacés.

## Mémoire externe optionnelle

```bash
oc memory enable git@github.com:USER/opencode-memory.git
oc memory status
oc memory capture-on
oc memory candidates
```

L'implémentation reste dans `opencode-memory-plugin`, désactivée par défaut pour
une nouvelle installation. Les configurations existantes sont conservées.
Codex utilise le MCP portable existant ; `accept`, `promote` et `push` restent des
opérations explicites. Voir [la documentation mémoire](docs/fr/MEMORY.md).

## Migration depuis Docker

Mettez le dépôt à jour, vérifiez les CLI natives, puis exécutez `just install`.
Les anciens réglages `OAT_RUNTIME=docker` et `OAT_SANDBOX_ENABLED=1` ne réactivent
pas les conteneurs. Les anciens conteneurs ne sont ni arrêtés ni supprimés
implicitement, et aucun volume n'est effacé.

Les credentials qui n'existent que dans un ancien volume Docker ne sont pas
importés automatiquement : utilisez `oc auth login` / `oc2 auth login` sur l'hôte.
Arrêtez ensuite explicitement l'ancienne stack avec `docker compose down` depuis
le toolkit ; **sans `-v`**, pour conserver les anciennes données. `oc2 server ...`
et `oc2 task ...` appartenaient à l'ancien wrapper Docker : utilisez maintenant les
commandes natives `serve`, `--server` ou `run`.

La CI principale teste le chemin natif, pas Docker/DinD. Les sources historiques
restent disponibles pour retour arrière et ne sont pas un second mode implicite.
`VERSION` et `CHANGELOG.md` restent les références des releases publiées.
