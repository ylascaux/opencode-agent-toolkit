# OpenCode V1 / V2 compatibility

The repository generates two native configurations from one source of truth (`scripts/generate-config`).

```text
opencode.jsonc      # OpenCode V1 stable
opencode.v2.jsonc   # OpenCode 2 beta
```

`just install`, `just config`, `just check`, `just doctor` and the launcher regenerate them automatically, preventing agent/command drift.

## Runtime selection

`.env` defaults to:

```dotenv
OPENCODE_MAJOR=1
```

Supported values:

- `1`: use `opencode` and V1 native config;
- `2`: use `opencode2` and V2 native config;
- `auto`: prefer `opencode2` when installed, otherwise use `opencode`.

Override for one command with `just v1` or `just v2`.

## Main syntax differences

| Concept | V1 | V2 |
|---|---|---|
| Agents map | `agent` | `agents` |
| Agent prompt | `prompt` | `system` |
| Permissions | `permission` | `permissions` |
| Shell permission | `bash` | `shell` |
| Subagent permission | `task` | `subagent` |
| Commands map | `command` | `commands` |

The generator translates the same logical policy to both formats.

## V2 plugin entrypoints

The observed OpenCode V2 beta-19425 build rejected file paths in the generated
`plugins` list and required directories instead. Because the `beta` package tag
is floating, the toolkit uses directory wrappers as a compatibility workaround;
each configured directory exposes an `index.ts` or `index.js` entrypoint. The
memory bridge generates its wrapper locally and re-exports the external plugin
adapter without changing the plugin checkout.

V1 keeps its existing direct file entrypoints.

## Native V2 context compaction

OpenCode V2 provides built-in context compaction, so the toolkit does not install or depend on third-party DCP/context-compression plugins.

The generated `opencode.v2.jsonc` explicitly enables the documented V2 defaults:

```jsonc
{
  "compaction": {
    "auto": true,
    "keep": {
      "tokens": 15000
    },
    "buffer": 20000
  }
}
```

This keeps automatic preflight compaction and one-shot context-overflow recovery enabled while preserving approximately 15k recent tokens and a 20k safety buffer. The values are intentionally explicit in the generated configuration so toolkit behavior stays deterministic across installations.

Do not add V1-only context-pruning plugins such as DCP to the V2 configuration unless they gain explicit V2 compatibility and provide a capability that native compaction does not cover.

## Nested delegation

The intended hierarchy includes two delegation levels:

```text
meta-router -> orchestrator -> specialist
```

The V1 config uses `subagent_depth: 2`; the V2 config uses the corresponding experimental setting.

## Recommendation

Keep V1 as the default runtime until the V2 behavior you depend on has been validated locally. V2 can be enabled per invocation without changing the rest of the toolkit.
