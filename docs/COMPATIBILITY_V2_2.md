# v2.2.0 Compatibility Verification

## Scope and method

This verification compares documented shipped v1.x, v2.0.x, and v2.1.x
contracts with stable v2.2.0. It uses public-export, release-contract,
architecture/import/dependency, CLI/MCP, persistence, recovery, integrity,
security, and workflow regression tests. Additive diagnostics and recovery
entry points do not replace an existing public entry point.

| Surface | v1.x / v2.0.x / v2.1.x contract | v2.2.0 result |
| --- | --- | --- |
| Python API | Documented root exports, result DTOs, and error hierarchy | Retained; no root export was removed or renamed. |
| Page workflow | Exactly one page; forward-only `Draft` → `Designed` → `Reviewed` → `Storyboarded` → `PromptBuilt` → `Generated` → `QualityChecked` → `Approved` | Retained; StateMachine remains the transition authority. |
| CLI | Existing project, workflow, batch, plugin, extension, security, diagnostics, health, and MCP commands | Retained; no existing command was replaced. |
| MCP | JSON-RPC initialization, tool contracts, DTO responses, package-derived server version | Retained; server metadata derives from `manga_director.__version__`. |
| Repository | `load`, `save`, `exists`, `delete`, and `list` port | Retained; query, integrity, and recovery helpers are optional additions. |
| Plugin API | Manifest, registry, manager, lifecycle, and dependency validation | Retained. |
| Extension SDK | Base classes, manifest, validator, loader, context, and packaging | Retained. |
| Notification | Factory/provider boundary and bounded retry behavior | Retained. |
| Web UI | Independently built presentation scaffold | Retained; no bundled HTTP contract was introduced. |
| FastAPI / REST / OpenAPI | Not shipped in the baseline | Still not shipped; no nonexistent endpoint or OpenAPI version is claimed compatible. |
| Automation | Not shipped in the baseline | Still not shipped; no nonexistent automation runtime is claimed compatible. |

## Versioning

`manga_director.__version__`, package metadata, MCP initialization metadata,
and the first-party SBOM package record use `2.2.0`. The independent frontend
package also uses `2.2.0`.

## Conclusion

No breaking change was identified for a shipped contract. RC1 feedback was
limited to release metadata, audit documentation, and validation corrections;
no product scope was expanded.
