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

## Nested delegation

The intended hierarchy includes two delegation levels:

```text
meta-router -> orchestrator -> specialist
```

The V1 config uses `subagent_depth: 2`; the V2 config uses the corresponding experimental setting.

## Recommendation

Keep V1 as the default runtime until the V2 behavior you depend on has been validated locally. V2 can be enabled per invocation without changing the rest of the toolkit.
