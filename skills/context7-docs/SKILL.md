## When to use

Use this skill when a task depends on current library, framework or API behavior, especially setup/configuration, generated code, migration guidance, or version-specific APIs.

## Retrieval method

1. Prefer Context7 over model memory when library/API details may have changed.
2. Resolve the library with the Context7 `resolve-library-id` tool unless an exact Context7 library ID is already known.
3. Query the selected library with `query-docs` for one focused concept at a time.
4. Prefer official or primary-project documentation when multiple matches exist.
5. If the user names a version, select version-specific documentation when available.
6. Use retrieved documentation as evidence; do not invent unsupported API names or options.

Do not call Context7 for repository-local code facts or generic programming concepts that do not depend on external library documentation.
