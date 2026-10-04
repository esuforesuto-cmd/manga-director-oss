# v5.0.0 RC1 Compatibility Review

## Baseline

v4.8.0 is the compatibility baseline. v5.0.0 RC1 adds only the
`manga_director.platform` package and leaves existing modules authoritative.

| Surface | RC result |
| --- | --- |
| Python API | Existing imports and behavior remain supported; platform facade is opt-in. |
| CLI | Existing command/help contract remains unchanged. |
| FastAPI / REST | Existing routes and OpenAPI behavior remain unchanged; no v5 route is registered. |
| MCP | Existing initialization and tool contract remain unchanged. |
| Web UI | Existing package metadata and UI contract remain unchanged except RC version metadata. |
| Repository | Save/reload remains owned by existing repositories; platform reports do not persist. |
| Workflow | StateMachine remains authoritative with existing one-Page safeguards. |
| Plugin / Extension SDK | Existing extension contracts remain unchanged; Unified SDK is additive. |
| Provider / Backend | Existing protocols and selection paths remain unchanged. |

No API removal, rename, data conversion, Core rewrite, or forced migration is
introduced by RC1.

