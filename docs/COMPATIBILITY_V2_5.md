# v2.5.0 Compatibility Verification

## Scope and method

This verification promotes RC1 evidence to stable `2.5.0` after release-only
metadata, documentation, package, and validation updates. It compares v1.x and
v2.0.x-v2.4.x contracts with v2.5 using public-export, architecture/import,
release-contract, CLI/MCP, repository, production, and documentation tests.

| Surface | v2.5.0 result |
| --- | --- |
| Python API | Root `Director`, `WorkflowEngine`, `WorkflowContext`, `Project`, `Page`, `ImageGenerator`, `Repository`, DTOs, and documented errors are retained. |
| Page workflow | One-page, forward-only StateMachine transitions, storyboard-before-generation, quality-before-approval, and explicit approval are retained. |
| CLI | Existing workflow, project, chapter, batch, plugin, MCP, diagnostics, health, database, security, and reporting commands are retained. |
| FastAPI / REST / MCP | FastAPI remains optional DTO-only observability delivery; MCP remains local JSON-RPC. No workflow REST surface is added. |
| Repository | The `load`, `save`, `exists`, `delete`, `list` port and persisted Project semantics are unchanged. |
| Plugin / Extension SDK | Registry, manifest, lifecycle, compatibility, context, and packaging contracts are unchanged. |
| Provider / Image Backend | Factory/Protocol contracts and Provider-neutral Agent behavior are unchanged. |
| Automation / Notification / Web UI | Existing outer delivery boundaries remain unchanged and do not acquire Core imports. |
| Diagnostics / Reporting / Health | Existing DTOs are retained; v2.5 helpers are optional additions under `manga_director.production`. |

## Versioning

Python package metadata, root import, MCP initialization, optional OpenAPI
metadata, frontend metadata, and SBOM use `2.5.0` through the canonical package
version source and its documented frontend derivation.

## Conclusion

No breaking change was identified. Stable release work is limited to reviewed
RC feedback, metadata promotion, documentation, and validation evidence.
