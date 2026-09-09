# Interface Web OpenCode

Le toolkit conserve une commande pratique `oc2 web`, mais OpenCode 2 bêta ne possède actuellement **pas** de sous-commande native `web`. Dans la CLI V2, `web` serait sinon interprété comme un répertoire de projet. Le launcher traduit donc automatiquement :

```text
oc2 web ...
        ↓
opencode2 serve ...
```

Le serveur V2 expose l'API et sert l'interface navigateur. Il utilise la même configuration V2 générée, les mêmes agents, plugins, modèles, permissions et garde-fous que le TUI.

## Démarrage rapide

Depuis le projet sur lequel OpenCode doit travailler :

```bash
cd ~/Projects/my-project
oc2 web --port 4096
```

Le launcher sélectionne `opencode2`, exporte `OPENCODE_CONFIG` vers `opencode.v2.jsonc`, puis traduit `web` en `serve`.

Tu peux aussi appeler la commande V2 native directement :

```bash
oc2 serve --hostname 127.0.0.1 --port 4096
```

Depuis le repository du toolkit :

```bash
just web-v2 --port 4096
just serve-v2 --port 4096
```

`just web` utilise la version OpenCode active. En V1 il appelle le vrai `opencode web`; en V2 le launcher applique l'alias `web -> serve`.

## Ouvrir l'interface

Contrairement à `opencode web` V1, `opencode2 serve` n'est pas une commande `web` dédiée. Avec un port fixe :

```bash
oc2 web --hostname 127.0.0.1 --port 4096
```

ouvre ensuite dans ton navigateur :

```text
http://127.0.0.1:4096
```

## Authentification

Les variables d'environnement sont héritées par le launcher et ne sont jamais copiées dans la configuration générée :

```bash
export OPENCODE_SERVER_USERNAME="yoann"
export OPENCODE_SERVER_PASSWORD="change-me"

oc2 web --hostname 127.0.0.1 --port 4096
```

Ne committe pas le mot de passe dans `.env`, `.env.local`, `opencode.v2.jsonc` ou un autre fichier versionné. Pour un secret durable, préfère le trousseau système ou un gestionnaire de secrets puis exporte la valeur au démarrage.

Attention : OpenCode 2 est encore en bêta et son mécanisme d'authentification serveur évolue. Si une version bêta refuse des identifiants pourtant corrects, vérifie d'abord la version installée et les issues V2 avant de modifier le toolkit.

## Accès local uniquement

Configuration recommandée sur ton Mac :

```bash
oc2 web --hostname 127.0.0.1 --port 4096
```

Puis :

```text
http://127.0.0.1:4096
```

## Accès depuis le réseau local

Pour rendre l'interface accessible depuis une autre machine :

```bash
export OPENCODE_SERVER_USERNAME="yoann"
export OPENCODE_SERVER_PASSWORD="change-me"

oc2 web --hostname 0.0.0.0 --port 4096
```

N'expose pas le serveur sur `0.0.0.0` sans authentification fonctionnelle.

## Web UI et TUI en même temps

Lance le serveur :

```bash
oc2 web --port 4096
```

Puis ouvre le navigateur sur :

```text
http://127.0.0.1:4096
```

Pour connecter également le TUI V2 au même serveur, utilise l'option V2 `--server` :

```bash
opencode2 --server http://127.0.0.1:4096
```

Cela remplace l'ancien workflow V1 basé sur `attach`, qui n'est pas une sous-commande V2 actuelle.

## API

La commande native V2 est :

```bash
oc2 serve --hostname 127.0.0.1 --port 4096
```

Elle expose le serveur HTTP V2 utilisé par les clients OpenCode. Le toolkit garde `oc2 web` comme alias ergonomique afin d'éviter que `web` soit interprété comme un répertoire.

## Vérification

Après modification du toolkit :

```bash
just test
just web-v2 --port 4096
```

Les tests du launcher vérifient que `oc2 web` sélectionne OpenCode V2, utilise `opencode.v2.jsonc`, traduit `web` en `serve`, conserve les arguments et transmet les variables d'authentification sans afficher le mot de passe.
