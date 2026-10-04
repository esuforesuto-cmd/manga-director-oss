# v2.4.0 Compatibility Verification

## Scope

This verification promotes RC1 evidence to stable v2.4.0 after release-only
corrective work. It compares v1.x and v2.0.x-v2.3.x contracts to the stable
metadata and confirms that no public removal or workflow semantic change was
introduced.

| Surface | v2.4.0 result |
| --- | --- |
| Python API | Root exports, type hints, result DTOs, and documented errors are retained. |
| CLI | Existing page, project, chapter, batch, database, plugin, extension, diagnostics, health, provider, and backend commands are retained. |
| FastAPI / REST | The optional DTO-only observability routes retain package-derived OpenAPI metadata; no workflow REST API is claimed. |
| MCP | Existing local JSON-RPC tools and responses are retained; diagnostic and health tools remain additive. |
| Workflow | Exactly one page, forward-only transitions, persisted storyboard before generation, quality before approval, and explicit human approval are retained. |
| Repository | The base five-method port remains unchanged; integrity, recovery, history, operation, and scalability helpers are optional. |
| Plugin / Extension SDK | Manifest, registry, lifecycle, validation, context, compatibility, and packaging contracts are retained. |
| Provider / Image Backend | Factory and Protocol contracts are retained; health, inventory, lifecycle, and diagnostics do not alter generation contracts. |
| Automation / Notification | Existing retry, resume, and delivery boundaries are retained. |
| Diagnostics / Health | Existing transport-neutral DTO surfaces remain additive and do not expose mutable Domain models. |

## Versioning

`manga_director.__version__`, project metadata, MCP initialization metadata,
optional OpenAPI metadata, frontend package metadata, SBOM, and stable release
assets use `2.4.0`. The stable frontend uses the same npm version with no
prerelease translation.

## Conclusion

No breaking change was found. No migration is required from supported v1.x or
v2.x lines.
