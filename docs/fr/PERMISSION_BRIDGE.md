# Bridge de permissions des sous-agents OpenCode V1

Dans OpenCode V1, une demande de permission appartient à la session qui l’a émise. Un sous-agent ou un sous-sous-agent peut donc atteindre une permission `ask` alors que l’utilisateur regarde toujours la session parente.

OpenCode expose actuellement des API TUI pour afficher un toast et ouvrir le sélecteur de sessions, mais il n’expose pas d’API plugin permettant de sélectionner directement une session par son ID. Le toolkit comble ce manque d’ergonomie sans modifier la décision de permission.

## Comportement

Quand `permission.asked` est émis par la session racine, le toolkit ne fait rien et laisse la TUI native d’OpenCode gérer la demande.

Quand `permission.asked` est émis par une session déléguée, le wrapper de fiabilité V1 :

1. retrouve la relation enfant/parent à partir des événements de session observés, avec `session.get` en solution de secours ;
2. affiche un toast d’avertissement indiquant l’agent, la session enfant et la permission demandée ;
3. ouvre le sélecteur de sessions natif d’OpenCode afin que l’utilisateur puisse sélectionner cet enfant et répondre au prompt de permission d’origine ;
4. ne modifie jamais la permission : le toolkit ne transforme jamais `ask` en `allow` ou `deny` ;
5. déduplique la répétition du même événement de permission pour éviter de spammer la TUI.

Le watchdog continue de considérer `WAITING_PERMISSION` comme une attente volontaire et non comme un blocage. Le bridge rend cette attente visible au lieu de la résoudre automatiquement.

## Configuration

Le comportement par défaut privilégie la visibilité :

```bash
PERMISSION_BRIDGE_TOAST=1
PERMISSION_BRIDGE_OPEN_SESSIONS=1
```

Définis `PERMISSION_BRIDGE_OPEN_SESSIONS=0` si tu veux conserver le toast sans que le toolkit ouvre automatiquement le sélecteur de sessions.

Définis `PERMISSION_BRIDGE_TOAST=0` pour désactiver le toast. Ce n’est pas recommandé sauf si une autre interface expose déjà de manière fiable les demandes de permissions des sous-agents.

## Limitation actuelle d’OpenCode

En septembre 2026, un plugin ne peut pas demander à la TUI de basculer directement vers une session enfant arbitraire par son ID. Le bridge ouvre donc le sélecteur de sessions natif et indique quel enfant attend. Si OpenCode ajoute plus tard une API `select-session` supportée, le bridge pourra évoluer pour donner automatiquement le focus à l’enfant bloqué.
