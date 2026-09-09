# Permissions des agents

Les permissions des agents ont une source de vérité unique et sont résolues lors de la génération de la configuration.

- `agents/_defaults/permissions.json` définit le socle commun hérité par tous les agents.
- `agents/<name>/permissions.json` est fusionné récursivement avec ce socle pour les surcharges propres à un agent.
- `agents/<name>/agent.json` définit le graphe de délégation via `parents` ; les permissions `task`/`subagent` sont générées depuis ce graphe et ne peuvent pas être surchargées manuellement dans `permissions.json`.
- Exécute `just config` après une modification d'agent ou de politique de permissions.

## Source de vérité unique

Le même arbre de permissions effectives alimente deux sorties :

1. les ACL runtime OpenCode V1/V2 ;
2. la section générée `## Effective capabilities` intégrée au prompt de chaque agent.

Les agents voient donc les capacités réellement accordées par le générateur. Il ne faut pas maintenir une seconde liste d'outils écrite manuellement dans les prompts.

La section générée sépare les permissions en :

- `ALLOW` : utilisable sans demande d'approbation ;
- `ASK` : nécessite l'approbation runtime/utilisateur ;
- `DENY` : ne doit jamais être tenté.

Les règles spécifiques à une ressource précisent les règles génériques. La délégation est également rendue explicitement : un agent ne voit comme sous-agents utilisables que ceux autorisés par sa permission `task`/`subagent` générée.

## Socle non interactif

Tous les agents doivent exécuter leurs outils et shells de manière non interactive. Cette règle est appliquée à plusieurs niveaux :

- le prompt commun interdit les pagers, TUI, éditeurs, REPL, menus et demandes de confirmation interactives ;
- la politique shell par défaut refuse explicitement des programmes interactifs courants comme `less`, `more`, `man`, les éditeurs de terminal, `top`/`htop`, `watch`, `fzf`, `lazygit` et `tig` ;
- les modes Git interactifs comme `git add -p` et `git rebase -i` sont refusés ;
- les commandes Git en lecture seule disposent de variantes `git --no-pager ...` explicitement autorisées ;
- le runtime injecte dans chaque shell agent des variables d'environnement désactivant pagers et prompts, en défense en profondeur.

Si une opération n'existe qu'en interface interactive et que l'agent ne connaît pas d'équivalent sûr et non interactif, il doit s'arrêter et déclarer le travail bloqué plutôt que d'attendre une saisie clavier.

## Posture de sécurité par défaut

Le socle conserve par ailleurs les limites suivantes :

- `websearch` : `allow` ;
- `webfetch` : `allow` ;
- commandes shell inconnues/non destructives : `ask` ;
- commandes Git sûres en lecture seule : `allow` ;
- modification normale de fichiers : `ask`, sauf surcharge `allow` des agents d'implémentation ;
- lecture de fichiers sensibles comme `.env`, clés SSH ou credentials AWS : `ask` ;
- répertoires externes : `ask`, avec des surcharges explicites par agent si nécessaire ;
- opérations clairement destructives comme suppression récursive, force-push, hard reset/clean, Terraform/OpenTofu/Terragrunt apply/destroy, Kubernetes delete et opérations similaires : `deny`.
