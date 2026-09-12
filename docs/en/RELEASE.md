# Release process

`VERSION` is the single release version source of truth. Tags use the corresponding `v<version>` form.

## Prepare a release

1. Update `VERSION` with the intended semantic version.
2. Add the matching `## [<version>]` section to `CHANGELOG.md`.
3. Run the complete release gate:

```bash
just release-check
```

This validates release metadata, runs `just check`, then runs the isolated offline runtime acceptance suite. Private-memory acceptance remains a separate CI integration because it requires dedicated access to the private memory-plugin repository.

## Merge before tagging

Release preparation must be merged normally through CI. Do not tag a feature or release branch.

After the release PR is merged, update local `main` and verify the metadata one last time:

```bash
git switch main
git pull --ff-only
python3 -B scripts/release-check --metadata-only --tag "v$(cat VERSION)"
```

Create an annotated tag on that exact merged commit:

```bash
git tag -a "v$(cat VERSION)" -m "opencode-agent-toolkit v$(cat VERSION)"
git push origin "v$(cat VERSION)"
```

A GitHub Release can then be created from that tag using the matching `CHANGELOG.md` section. The repository intentionally does not auto-publish releases or require `contents: write` in normal CI.

## Release requirements

Before tagging, all mandatory checks on the merged commit should be green:

- standard `test` job;
- sandbox security checks;
- runtime/DinD checks;
- offline external-project acceptance;
- Docker/OpenCode V2 HTTP smoke.

The private-memory job must never emulate the MCP server. When the dedicated inter-repository token is configured it tests the real pinned plugin; otherwise the integration is explicitly reported as skipped.

## Version policy

Until the local multi-runtime interfaces are considered stable for external users, use `0.x.y` releases:

- patch: fixes and compatible hardening;
- minor: new runtime adapters, portable capabilities, or lifecycle features;
- `1.0.0`: only after the public CLI/config contracts are intentionally declared stable.
