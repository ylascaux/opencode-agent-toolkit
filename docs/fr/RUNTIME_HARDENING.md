# Durcissement du runtime watchdog

Ce document résume les invariants techniques ajoutés autour du watchdog afin d'éviter les faux blocages, les faux positifs anti-loop, les budgets appliqués à la mauvaise session et les agents délégués bloqués dans des programmes de terminal interactifs.

## Call IDs de fallback

Quand OpenCode fournit un `callID`, le runtime l'utilise directement.

Quand aucun ID natif n'est disponible, le toolkit crée un ID unique et conserve une file FIFO par signature `session + tool + arguments`. Deux appels identiques lancés en parallèle obtiennent donc deux IDs distincts, et les événements `execute.after` consomment les IDs dans l'ordre de lancement.

Cette mécanique empêche les réservations fantômes qui pourraient bloquer artificiellement la queue de sous-agents.

## Anti-loop sensible au progrès

La détection `même outil + mêmes arguments + même résultat` est limitée à une fenêtre de progrès.

Un progrès matériel (`session.diff`, édition de fichier, todo mis à jour, réponse à une permission, ou résultat d'outil distinct réussi) avance l'époque de progrès. Un appel identique observé après cette frontière n'est donc pas considéré comme la continuation d'une ancienne boucle.

## Résolution des sessions sur les événements message

Les événements de message contiennent à la fois un ID de message et un ID de session. Le watchdog privilégie toujours `sessionID` pour mettre à jour l'activité, le coût et les limites runtime.

Cela garantit notamment que `MAX_CHILD_COST` et `MAX_RUN_COST` s'appliquent à la session agent concernée et non à un objet message éphémère.

## Invariant shell non interactif

L'exécution shell des agents est non interactive par construction, pas seulement par convention dans le prompt.

La politique partagée `.opencode/plugins/non-interactive-shell.js` injecte :

- `PAGER=cat` ;
- `GIT_PAGER=cat` ;
- `GH_PAGER=cat` ;
- `SYSTEMD_PAGER=cat` ;
- `BAT_PAGER=cat` ;
- `AWS_PAGER=` ;
- `GIT_TERMINAL_PROMPT=0` ;
- `GH_PROMPT_DISABLED=1` ;
- `TF_INPUT=0` ;
- `TF_IN_AUTOMATION=1` ;
- `CI=1`.

OpenCode V1 applique cette politique via le hook plugin `shell.env`. OpenCode V2 l'applique via le hook shell `create.before` avant la création de chaque shell agent. V2 échoue volontairement en mode fermé si ce hook shell n'est pas disponible : ignorer silencieusement cet invariant pourrait laisser un sous-agent attendre indéfiniment une saisie clavier.

Cette couche runtime complète la politique de permissions par défaut, qui refuse les pagers/TUI/éditeurs courants et les modes Git interactifs, ainsi que le prompt commun, qui impose de terminer en `BLOCKED` lorsqu'aucune méthode sûre et non interactive n'est connue.

## Tests comportementaux

`just runtime-test` exécute des tests Node qui vérifient :

- IDs de fallback uniques et FIFO pour des appels identiques concurrents ;
- reset de l'anti-loop après progrès réel ;
- politique de retry provider (`401/404` terminaux, `429/5xx` bornés) ;
- libération d'une réservation de sous-agent après `execute.after` ;
- application du budget de coût au child réel ;
- exemption de `WAITING_PERMISSION` du stall timeout puis reprise de la détection après réponse ;
- injection de l'environnement shell non interactif partagé, y compris le comportement `shell.env` de V1.

Les tests Python vérifient également que chaque prompt d'agent généré contient le contrat non interactif et que sa carte de capacités `ALLOW`/`ASK`/`DENY` correspond à l'arbre de permissions V1 effectif généré.

`just check` inclut ces tests en plus de la validation de la configuration générée.
