# v2.3.0 RC1 Compatibility Audit

## Scope and method

This audit compares documented v1.x, v2.0.0, v2.1.0, and v2.2.0 shipped
contracts against `2.3.0rc1`. It combines root-export, architecture/import,
release-contract, CLI/MCP, recovery/integrity, enterprise, and documentation
link tests with manual boundary inspection.

| Surface | Prior contract | v2.3.0rc1 result |
| --- | --- | --- |
| Python API | Root `Director`, `WorkflowEngine`, `WorkflowContext`, `Project`, `Page`, `ImageGenerator`, `Repository`, DTOs, and documented errors | Retained; no root export removed or renamed. |
| Page workflow | Exactly one page and forward-only StateMachine transitions | Retained; `run` stops at `QualityChecked` and approval remains explicit. |
| CLI | Existing workflow, project, chapter, batch, plugin, MCP, diagnostics, and health commands | Retained; new health/self-check commands are additive. |
| MCP | Local JSON-RPC, existing tools, DTO responses, package-derived version | Retained; health and integrity tools are additive DTO-only tools. |
| FastAPI / REST / OpenAPI | No general workflow REST API | Retained; optional v2.3 observability adapter adds only documented DTO routes. |
| Repository | `load`, `save`, `exists`, `delete`, `list` port | Retained; scalability, integrity, and recovery helpers do not change it. |
| Plugin / Extension SDK | Registry, manifest, lifecycle, validation, context, packaging contracts | Retained; caching, health, and diagnostics remain outer-layer additions. |
| Provider / Image Backend | Factory and Protocol-based selection; Agents are provider-neutral | Retained; lifecycle/health metadata does not change `generate` contracts. |
| Web UI | Independent presentation scaffold | Retained; no Python Domain model import and no bundled workflow HTTP service. |

## Versioning

`manga_director.__version__`, package metadata, MCP initialization metadata,
optional OpenAPI metadata, and the SBOM record use `2.3.0rc1`. The independent
frontend uses the equivalent npm prerelease form `2.3.0-rc.1`.

## Conclusion

No breaking change was identified. RC feedback is limited to corrective work;
new capabilities belong after the v2.3 stable release.
