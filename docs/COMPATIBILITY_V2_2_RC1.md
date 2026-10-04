# v2.2.0 RC1 Compatibility Audit

## Scope and method

This audit compares the documented shipped v1.x, v2.0.0, and v2.1.0 contracts
with the v2.2.0rc1 source. It combines root-export and release-contract tests,
CLI/MCP smoke tests, architecture/import tests, and an inspection of versioned
public documentation. Additive diagnostics and recovery APIs do not replace an
existing entry point.

| Surface | v1.x / v2.0.0 / v2.1.0 contract | v2.2.0rc1 result |
| --- | --- | --- |
| Python API | Root `Director`, `WorkflowEngine`, `WorkflowContext`, `Project`, `Page`, `ImageGenerator`, `Repository`, result DTOs, and documented errors | Retained; no root export was removed or renamed. |
| Page workflow | Exactly one page; forward-only Draft → Designed → Reviewed → Storyboarded → PromptBuilt → Generated → QualityChecked → Approved | Retained; `StateMachine` remains the transition authority. |
| CLI | Existing project, workflow, batch, plugin, extension, security, diagnostics, health, and MCP commands | Retained; diagnostics/health additions are additive. |
| MCP | JSON-RPC initialization, existing tools, DTO responses, package-derived server version | Retained; health/diagnostic tools are additive and return DTOs. |
| Repository | `load`, `save`, `exists`, `delete`, `list` and interface-only dependency from application code | Retained; optional query, integrity, and recovery helpers do not change the base protocol. |
| Plugin API | Manifest, registry, manager, lifecycle, dependency validation | Retained; caches and lazy loading preserve public signatures. |
| Extension SDK | Base extensions, manifest, validator, loader, context, packaging | Retained; validation and context paths are optimized behind existing APIs. |
| Web UI | Independently built presentation scaffold | Retained; no bundled HTTP contract is introduced. |
| FastAPI / REST / OpenAPI | Not shipped in the baseline | Still not shipped; no nonexistent endpoint or OpenAPI version is claimed compatible. |
| Automation | Not shipped in the baseline | Still not shipped; no nonexistent automation runtime is claimed compatible. |

## Versioning

`manga_director.__version__`, package metadata, MCP initialization metadata,
and the first-party SBOM package record use `2.2.0rc1`. The independent
frontend package uses npm prerelease syntax: `2.2.0-rc.1`.

## Conclusion

No breaking change was identified for the shipped contracts. RC feedback must
remain limited to corrective changes; new capabilities belong after the v2.2
stable release process.
