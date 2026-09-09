# Durcissement du runtime watchdog

Ce document résume les invariants techniques ajoutés autour du watchdog afin d'éviter les faux blocages, les faux positifs anti-loop et les budgets appliqués à la mauvaise session.

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

## Tests comportementaux

`just runtime-test` exécute des tests Node qui vérifient :

- IDs de fallback uniques et FIFO pour des appels identiques concurrents ;
- reset de l'anti-loop après progrès réel ;
- politique de retry provider (`401/404` terminaux, `429/5xx` bornés) ;
- libération d'une réservation de sous-agent après `execute.after` ;
- application du budget de coût au child réel ;
- exemption de `WAITING_PERMISSION` du stall timeout puis reprise de la détection après réponse.

`just check` inclut désormais ces tests en plus des tests Python et de la génération/validation des configurations.
