# v2.3.0 Compatibility Verification

## Scope

This verification promotes RC1 evidence to stable v2.3.0 after corrective
review only. It compares v1.x, v2.0.x, v2.1.x, and v2.2.x contracts against
the stable metadata and confirms no public removal or semantic change.

| Surface | v2.3.0 result |
| --- | --- |
| Python API | Root exports, type hints, results, and documented errors retained. |
| CLI | Existing commands preserved; health/self-check additions remain additive. |
| FastAPI | Optional DTO-only observability routes retain package-derived OpenAPI version; no workflow API is claimed. |
| MCP | Existing local JSON-RPC tools and responses retained; new diagnostic tools remain additive. |
| Workflow | Exactly one page, forward-only transitions, persisted storyboard requirement, quality-before-approval, and explicit approval retained. |
| Repository | Base five-method port retained; query/scalability/integrity/recovery helpers are optional. |
| Plugin / Extension SDK | Manifest, registry, lifecycle, validator, context, and packaging contracts retained. |
| Provider / Image Backend | Factories and Protocols retained; lifecycle health does not alter generation contracts. |
| Automation / Notification | Existing retry/recovery and DTO boundaries retained. |

## Versioning

`manga_director.__version__`, project metadata, MCP initialization metadata,
optional OpenAPI metadata, frontend package metadata, SBOM, and release assets
use `2.3.0`. There is no prerelease version translation for the stable
frontend package.

## Conclusion

No breaking change was found. No migration is required from supported v1.x or
v2.x lines.
