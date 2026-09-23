# OpenCode Agent Toolkit — native edition

`oc` lance OpenCode V1 sur la machine. `oc2` lance OpenCode V2 sur la machine.
Aucun conteneur, DinD, socket Docker, serveur permanent géré par le toolkit,
watchdog ou plugin d'approbation n'est nécessaire.

Le catalogue d'agents, les modèles par niveau et les skills restent partagés avec
la synchronisation Codex. Le chemin natif utilise une politique d'exécution courte,
sans les anciennes consignes d'approbation des leads.

## Installation

Prérequis : Bash, Python 3.11+, `just`, et le binaire du runtime utilisé :
`opencode` pour V1, `opencode2` pour V2. Les deux ne sont pas obligatoires si vous
n'utilisez qu'une version. Installez les CLI avec leur procédure officielle ;
le toolkit ne remplace pas vos versions ni vos comptes.

```bash
just install
just doctor
```

L'installation génère les configurations et crée les liens `~/.local/bin/oc` et
`~/.local/bin/oc2`. Ajoutez `~/.local/bin` au PATH si nécessaire. Elle ne lance
ni `npm install`, ni `pip install`, ni Docker. Une `.env` existante et les
surcharges de `.env.local` sont conservées.

Depuis le projet à modifier :

```bash
oc
oc2
oc2 run "Corrige le bug et lance les tests"
oc2 auth login
```

`oc` sélectionne toujours V1 et `oc2` toujours V2. Le répertoire courant, HOME et
les comptes natifs sont conservés. `OPENCODE_BIN=/chemin/vers/le/binaire` permet
un chemin explicite. Pour la TUI et `run`, V2 utilise `--standalone` par défaut,
afin de ne pas se reconnecter à un ancien serveur Docker. Une sélection explicite
`--server URL` est respectée. `oc2 serve ...` reste le serveur natif, au premier plan.

## Commandes utiles

```bash
just install                 # installer ou régénérer les lanceurs locaux
just profile copilot         # conserver les surcharges de .env.local
just config                  # régénérer les deux configurations, sans réseau
just doctor                  # vérifier binaires et dérive de configuration
just test                    # tests contributeur Python et Node
just uninstall               # retirer seulement les liens gérés
```

`just oc`, `just oc2`, `just sync`, `just codex` et `just memory` sont des raccourcis
quand on se trouve dans le toolkit. Depuis un autre dépôt, utilisez directement
`oc`/`oc2` pour conserver le bon contexte de projet.

## Contribuer

Toute modification du toolkit passe par une PR ; les checks et tests obligatoires
pertinents doivent être verts avant le merge. Voir le [guide de contribution](docs/fr/CONTRIBUTING.md)
([English](docs/en/CONTRIBUTING.md)).

Les configurations sont autonomes : prompts intégrés, remplacements atomiques,
pas de chemin `/opt/oat`, pas de wrapper shell sandbox, pas de plugins de contrôle
ni de limite de pas ajoutée par le toolkit. Le meta-router et la délégation courte
restent disponibles. Les interdictions globales Git distant, SSH, AWS et kubectl
liées à l'ancienne sandbox sont retirées ; les interdictions plus précises des
opérations destructives restent conservées. Les validations explicites et les règles propres à votre
projet ne sont pas désactivées. Le mode natif n'est **pas une isolation de sécurité**.

## Codex : synchronisation conservée

```bash
oc sync codex --dry-run
oc sync codex

cd /chemin/vers/mon-projet
oc codex install
oc codex doctor
```

La source reste `agents/<nom>/` et `skills/<nom>/`. `--dry-run` et `--check` ne
modifient aucun fichier. La génération Codex et son installation ne nécessitent
ni Docker, ni OpenCode, ni authentification fournisseur. Les protections contre
l'écrasement de fichiers utilisateur restent inchangées.

```bash
oc codex install --with-memory
oc codex uninstall
```

`oc sync opencode` et `oc sync all` restent des exports de l'adapter historique.
Pour la configuration OpenCode utilisée au quotidien, utilisez `just config` ;
les lanceurs natifs la régénèrent également avant de démarrer.

## Mémoire OpenCode V2 : plugin tiers `opencode-mem`

`oc2` charge par défaut le paquet publié `opencode-mem@2.26.0`. Ce plugin est
maintenu hors de ce dépôt et OpenCode V2 l'installe via son mécanisme natif de
plugins. Le toolkit ne clone, ne build et ne maintient donc plus son plugin
mémoire maison pour V2.

Au premier lancement, si `~/.config/opencode/opencode-mem.jsonc` n'existe pas,
le toolkit crée une configuration minimale pour rendre l'auto-capture utile
immédiatement : le provider est déduit du profil `MODEL_*` actif et
`opencodeModel` vaut `inherit`, afin d'utiliser le modèle réel de la session.
Un fichier existant n'est jamais écrasé.

La mémoire est locale, par projet par défaut, avec recherche vectorielle,
auto-capture à l'idle et réinjection des souvenirs pertinents. Le serveur Web du
plugin est désactivé dans la configuration minimale créée par le toolkit ; vous
pouvez le réactiver dans le fichier du plugin si vous souhaitez son interface.

Pour désactiver la mémoire V2 ou changer le paquet épinglé :

```bash
# .env.local
OAT_OC2_MEMORY_ENABLED=0

# ou, pour tester explicitement une autre version
OAT_OC2_MEMORY_PLUGIN=opencode-mem@2.26.0
```

Si la déduction du provider ne convient pas :

```bash
OAT_OC2_MEMORY_PROVIDER=github-copilot
```

Le premier usage du moteur d'embeddings local peut télécharger son modèle. Les
outils mémoire manuels du plugin restent disponibles même si l'auto-capture ne
peut pas utiliser de provider.

### Compatibilité V1 / Codex

L'ancien bridge privé `oc memory ...` reste présent uniquement pour ne pas casser
les usages V1/Codex existants. Il n'est plus chargé par `oc2`. De même,
`oc codex install --with-memory` reste un chemin de compatibilité séparé et ne
conditionne pas le fonctionnement de la mémoire OpenCode V2.

## Migration depuis Docker

Après avoir récupéré cette version, lancez `just install`. Les anciennes valeurs
`OAT_RUNTIME=docker`, `OAT_SANDBOX_ENABLED=1` et `PLAN_APPROVAL_MODE=...` ne peuvent
plus renvoyer les lanceurs vers Docker ou l'ancien workflow d'approbation.

Les anciens conteneurs et volumes ne sont **pas** arrêtés ou supprimés automatiquement.
Les comptes présents uniquement dans leurs volumes ne sont pas importés : reconnectez
le fournisseur avec le CLI natif au besoin. Aucun secret n'est copié vers Git.

Les scripts Docker/sandbox et l'adapter historique restent dans le dépôt pour
compatibilité et référence, mais ne sont plus le chemin d'installation ou de lancement.
`VERSION` et `CHANGELOG.md` restent les références de publication ; cette PR ne crée
pas de release et ne met pas à jour les CLI sans votre intervention.
