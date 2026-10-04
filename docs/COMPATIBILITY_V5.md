# v5.0.0 Compatibility Verification

## Baseline

v4.8.0 is the compatibility baseline. v5.0.0 adds the optional
`manga_director.platform` package without changing existing module ownership.

| Surface | Final result |
| --- | --- |
| Python API | Existing imports and behavior remain supported; platform facade is opt-in. |
| CLI | Existing commands, help, and exit contracts remain unchanged. |
| FastAPI / REST | Existing routes and OpenAPI behavior remain unchanged; no v5 route is registered. |
| MCP | Existing initialization and tool contracts remain unchanged. |
| Web UI | Existing UI contracts remain unchanged; metadata is synchronized to 5.0.0. |
| Repository | Save/reload remains owned by existing repositories; platform reports do not persist. |
| Workflow | StateMachine retains all one-Page and stage safeguards. |
| Plugin / Extension SDK | Existing extension contracts remain unchanged; Unified SDK is additive. |
| Provider / Backend | Existing protocols and paths remain unchanged. |

No removal, rename, forced migration, data conversion, or Core redesign is
introduced by v5.0.0.

