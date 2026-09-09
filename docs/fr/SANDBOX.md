# Sandbox des agents et diagnostics cloud manuels

Le toolkit peut exécuter les commandes shell normales des agents dans une sandbox de développement jetable tout en gardant le système hôte, les credentials et les identités cloud hors de cette sandbox.

## Modèle de sécurité

Quand `OAT_SANDBOX_ENABLED=1`, un lancement OpenCode crée un conteneur Docker/Podman persistant pour le dépôt courant. Le conteneur ne vit que pendant la session OpenCode afin que les téléchargements Nix, l'état `direnv` et les caches de build restent utiles entre plusieurs commandes d'agents.

```text
OpenCode / agents sur l'hôte
        |
        | commande shell normale
        v
politique de permissions OpenCode
        |
        v
sandbox de dev persistante --> dépôt RW

Besoin d'une preuve AWS/Kubernetes
        |
        v
l'agent propose la commande exacte en lecture seule
        |
        v
l'utilisateur l'exécute sur l'hôte de confiance
        |
        v
l'utilisateur colle le résultat nettoyé
```

La sandbox reçoit :

- le dépôt courant dans `/workspace` en lecture/écriture ;
- `.github` surmonté en lecture seule quand il existe ;
- un accès Internet via le réseau bridge du runtime de conteneur ;
- un socle d'outils basé sur Nix ;
- des limites CPU, mémoire et nombre de processus.

Elle ne reçoit **pas** `~/.aws`, `~/.ssh`, `~/.kube`, les credentials Azure/GCloud, les credentials du CLI GitHub, `SSH_AUTH_SOCK` ni le socket Docker de l'hôte.

Le conteneur est lancé avec `--cap-drop=ALL` et `no-new-privileges`. Le processus est root dans le conteneur pour permettre l'écriture dans le store Nix, mais sans capabilities Linux et sans montage de credentials ou sockets de l'hôte. Sur Docker Desktop macOS, il reste en plus derrière la VM Linux de Docker.

## Nix et direnv

L'image de base reste volontairement légère. Elle contient uniquement le socle nécessaire pour inspecter/modifier un dépôt et amorcer son environnement : Git, Nix, direnv/nix-direnv, Python, curl/wget, jq/yq, ripgrep/fd, just, shellcheck, hadolint et actionlint.

Go, Rust/Cargo, Node.js, PHP/Composer, Helm, OpenTofu, Terragrunt et les autres toolchains spécifiques doivent venir du `flake`, de `devenv` ou de la configuration Nix du dépôt cible. On garde ainsi une image par défaut légère tout en utilisant les versions exactes requises par chaque projet.

AWS CLI et kubectl ne font volontairement pas partie de l'image de base. Un dépôt peut toujours fournir des outils supplémentaires via Nix, mais aucun credential AWS/Kubernetes de l'hôte n'est monté et la politique OpenCode par défaut interdit l'exécution directe de `aws ...` et `kubectl ...`.

Avant une commande shell normale, le runner cherche le `.envrc` le plus proche, exécute `direnv allow` **dans la sandbox**, exporte l'environnement puis lance la commande. Un `.envrc` est du code exécutable contrôlé par le dépôt ; le fait de l'exécuter dans la sandbox est précisément la frontière de sécurité recherchée.

## Activer la sandbox

```bash
just sandbox-on
just sandbox-doctor
```

`just sandbox-on` construit l'image et enregistre `OAT_SANDBOX_ENABLED=1` dans `.env.local`. Pour la désactiver :

```bash
just sandbox-off
```

Commandes utiles :

```bash
just sandbox-build
just sandbox-doctor
just sandbox-clean
```

La sandbox reste opt-in pour compatibilité avec les installations existantes.

## Debug AWS et Kubernetes

Les diagnostics AWS et Kubernetes sont **manuels uniquement**.

Les agents ne doivent jamais exécuter `aws ...` ni `kubectl ...`. Lorsqu'ils ont besoin d'une preuve runtime, ils fournissent la plus petite commande utile, expliquent ce qu'elle vérifie et demandent à l'utilisateur de l'exécuter sur son environnement de confiance. L'utilisateur colle ensuite le résultat nettoyé dans la conversation.

Exemple :

```text
Agent :
  Lance :
  kubectl get pods -n payments -o wide

  Cela permet de vérifier si le workload concerné est bien planifié et s'il redémarre.
  Colle-moi le résultat ; cette commande ne devrait pas exposer de secret.

Utilisateur :
  <résultat>

Agent :
  analyse la preuve puis ne demande la commande suivante que si nécessaire
```

Privilégier les commandes de diagnostic en lecture seule :

```bash
aws sts get-caller-identity
aws ec2 describe-instances ...
aws logs tail ...

kubectl get ...
kubectl describe ...
kubectl logs ...
kubectl events ...
kubectl auth can-i ...
```

Ne jamais demander à l'utilisateur de renvoyer des secrets, tokens, kubeconfigs, mots de passe ou clés privées. Éviter notamment `aws secretsmanager get-secret-value`, les lectures SSM déchiffrées, la récupération de tokens d'autorisation ou `kubectl get secrets -o yaml/json`. Si une sortie peut contenir des valeurs sensibles, demander une version filtrée ou masquée.

Ce flux manuel apporte deux garanties importantes : les credentials cloud n'entrent jamais dans le runtime agent et l'utilisateur voit chaque commande visant l'infrastructure réelle avant son exécution.

## Frontière réseau

Le mode réseau par défaut est `bridge` car Nix, les gestionnaires de paquets et les outils de source ont besoin d'Internet. Le réseau bridge Docker/Podman n'est **pas** une allowlist egress/LAN stricte et ne doit pas être considéré comme une isolation du réseau privé.

Pour des environnements plus sensibles, placer la sandbox derrière un proxy/firewall egress et n'autoriser que les registres et services publics nécessaires. Cette limite est explicitement documentée dans `sandbox/policy.json`.

## Builds Docker

Le socket Docker de l'hôte n'est jamais monté. La sandbox standard peut analyser et linter les Dockerfiles mais ne peut pas contrôler le daemon Docker de l'hôte. Si de vrais builds d'images deviennent nécessaires, utiliser plus tard un profil BuildKit rootless séparé plutôt que d'exposer `/var/run/docker.sock`.

## Frontières de confiance

Les couches prévues sont :

1. prompt et carte de capacités générée de l'agent ;
2. permissions OpenCode `allow / ask / deny` ;
3. routage des commandes vers la sandbox ;
4. isolation filesystem/ressources du conteneur ;
5. absence de credentials et sockets hôte ;
6. diagnostics AWS/Kubernetes manuels exécutés par l'utilisateur.

Une défaillance d'une couche ne doit donc pas donner automatiquement accès au filesystem de l'hôte ou au cloud.
