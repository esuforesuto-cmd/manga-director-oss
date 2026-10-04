# v2.1.0 Compatibility Audit

## Method

The v1.x and v2.0 documented public contracts, executable CLI/MCP entry points,
persisted Project semantics, and release-contract tests were compared with the
v2.1.0 source and distribution. This checkout retains a `2.0.0rc1` benchmark
wheel rather than a `2.0.0` tag object, so package-level performance comparison
uses that retained artifact while API compatibility is based on the published
contracts.

## Result

| Surface | v1.x / v2.0 contract | v2.1.0 result |
| --- | --- | --- |
| Python API | Stable root exports, typed DTOs, and exceptions | Preserved; `__version__` remains an additive introspection export. |
| Workflow | One page, forward-only states, explicit approval | Preserved; state and workflow regressions pass. |
| CLI | Existing page, project, chapter, batch, MCP, and Plugin commands | Preserved; installed-wheel smoke passes. |
| MCP | Local stdio JSON-RPC with validated DTOs | Preserved; server version derives from the package version. |
| Repository | Port, local persistence, database adapters, migration boundary | Preserved; local and SQLite migration tests pass. |
| Plugin / SDK | Local manifest, registry, lifecycle, and SDK contracts | Preserved; packaging and version-compatibility tests pass. |
| FastAPI / REST | Not shipped in this baseline | Still not shipped; no nonexistent API is claimed compatible. |
| Automation | Not shipped in this baseline | Still not shipped; no nonexistent API is claimed compatible. |
| Web UI | Typed client for a separately compatible HTTP service | Preserved as an independently built and tested presentation scaffold. |

## Conclusion

No shipped v1.x or v2.0 public contract was removed, renamed, or made more
permissive. v2.1.0 is backward compatible for the listed shipped surfaces.
