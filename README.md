# OpenCode Agent Toolkit

Un toolkit multi-agents pour [OpenCode](https://opencode.ai/) : il génère une configuration V1/V2 à partir d'agents autonomes, applique des garde-fous de fiabilité et de permissions, puis fournit un lanceur et des diagnostics pour travailler sur un projet.

Le runtime Docker garde `oc`/`oc2` isolés du socket Docker hôte. `oc2` expose aussi le callback OAuth OpenAI uniquement sur `127.0.0.1:1455` afin que l'authentification navigateur fonctionne lorsque OpenCode V2 tourne dans le container.
