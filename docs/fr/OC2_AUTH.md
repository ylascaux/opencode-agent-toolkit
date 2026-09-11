# Authentification OpenCode V2 dans Docker

Le runtime OC2 du toolkit sépare deux authentifications différentes :

- `OPENCODE_SERVER_PASSWORD` protège l'accès du client local au serveur OC2.
- Les credentials fournisseurs (OpenAI, GitHub Copilot, etc.) sont stockés dans le home persistant du conteneur, notamment dans `/root/.local/share/opencode/auth.json`.

## OpenAI / ChatGPT Pro ou Plus

Le flow OAuth navigateur d'OpenAI ouvre son callback sur `localhost:1455` dans le processus OpenCode. Quand `auth login` tourne dans le conteneur, ce listener est attaché au loopback du conteneur et n'est pas joignable par le navigateur du Mac via un simple port publish Docker.

Utiliser le raccourci du toolkit :

```bash
oc2 auth openai
```

Il lance explicitement :

```bash
opencode2 auth login -p openai -m "ChatGPT Pro/Plus (headless)"
```

Ce flow utilise l'authentification device/headless et ne dépend pas d'un callback HTTP local.

Vérifier ensuite les credentials :

```bash
oc2 auth list
```

Puis, si nécessaire :

```bash
oc2 server restart
```

## Login interactif générique

`oc2 auth login` reste disponible pour les autres fournisseurs. Le toolkit affiche un avertissement avant le sélecteur interactif afin de rappeler que, pour OpenAI dans Docker, il faut choisir `ChatGPT Pro/Plus (headless)` et non le mode `browser`.
