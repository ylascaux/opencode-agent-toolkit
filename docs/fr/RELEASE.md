# Processus de release

`VERSION` est l’unique source de vérité pour la version publiée. Les tags utilisent la forme correspondante `v<version>`.

## Préparer une release

1. Mettre `VERSION` à la version sémantique souhaitée.
2. Ajouter la section `## [<version>]` correspondante dans `CHANGELOG.md`.
3. Exécuter le gate complet :

```bash
just release-check
```

Cette commande valide les métadonnées de release, exécute `just check`, puis l’acceptance runtime offline et isolée. Le test de la mémoire privée reste une intégration CI séparée, car il nécessite un accès dédié au dépôt privé du plugin mémoire.

## Merger avant de taguer

La préparation d’une release doit passer par une PR et la CI normale. Ne jamais taguer directement une branche de feature ou de release.

Après merge, mettre `main` à jour et revérifier les métadonnées :

```bash
git switch main
git pull --ff-only
python3 -B scripts/release-check --metadata-only --tag "v$(cat VERSION)"
```

Créer ensuite un tag annoté sur ce commit mergé précis :

```bash
git tag -a "v$(cat VERSION)" -m "opencode-agent-toolkit v$(cat VERSION)"
git push origin "v$(cat VERSION)"
```

Une GitHub Release peut ensuite être créée depuis ce tag en reprenant la section correspondante de `CHANGELOG.md`. Le dépôt ne publie volontairement rien automatiquement et la CI normale n’a pas besoin de permission `contents: write`.

## Conditions avant tag

Les checks obligatoires du commit mergé doivent être verts :

- tests standards ;
- sécurité sandbox ;
- runtime/DinD ;
- acceptance offline depuis un projet externe ;
- smoke Docker/OpenCode V2 HTTP.

Le job `private-memory` ne doit jamais simuler le MCP. Avec le token inter-repo dédié, il teste le vrai plugin piné ; sinon le skip doit rester explicite.

## Politique de version

Tant que les interfaces multi-runtime locales ne sont pas déclarées stables pour des utilisateurs externes, utiliser des releases `0.x.y` :

- patch : corrections et hardening compatibles ;
- minor : nouvel adapter runtime, nouvelle capacité portable ou évolution de lifecycle ;
- `1.0.0` : uniquement lorsque les contrats publics CLI/config sont volontairement figés.
