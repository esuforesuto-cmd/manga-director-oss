# v2.5.0 RC1 Compatibility Audit

## Scope and method

This audit compares documented v1.x, v2.0.x, v2.1.x, v2.2.x, v2.3.x, and v2.4.x
contracts against `2.5.0rc1`. It combines root-export, architecture/import,
release-contract, CLI/MCP, repository/integrity, production/readiness, and
documentation-link tests with a manual dependency-direction review.

| Surface | v2.5.0rc1 result |
| --- | --- |
| Python API | Root `Director`, `WorkflowEngine`, `WorkflowContext`, `Project`, `Page`, `ImageGenerator`, `Repository`, DTOs, and documented errors are retained. |
| Page workflow | Exactly one page, forward-only StateMachine transitions, persisted storyboard before generation, quality-before-approval, and explicit approval are retained. |
| CLI | Existing workflow, project, chapter, batch, plugin, MCP, diagnostics, health, database, and security commands are retained. |
| FastAPI / REST / MCP | FastAPI remains DTO-only observability delivery; MCP remains local DTO JSON-RPC. Package-derived metadata remains aligned. |
| Repository | The `load`, `save`, `exists`, `delete`, `list` port is unchanged; integrity, recovery, maintenance, and readiness helpers are additive. |
| Plugin / Extension SDK | Registry, manifest, lifecycle, compatibility, context, and packaging contracts are unchanged. |
| Provider / Image Backend | Factory/Protocol contracts and provider-neutral Agent behavior are unchanged; reports remain diagnostic-only. |
| Automation / Notification / Web UI | Existing outer delivery boundaries remain unchanged and do not acquire Core imports. |
| Diagnostics / Health / Reporting | Existing DTOs are retained; v2.5 readiness DTOs are optional additions under `manga_director.production`. |

## Versioning

Python package metadata, root import, MCP initialization, optional OpenAPI
metadata, and SBOM use `2.5.0rc1`. The independent npm frontend uses the valid
equivalent `2.5.0-rc.1`.

## Conclusion

No breaking change was identified. RC feedback is restricted to corrective
release work; new workflow, provider, backend, cloud, marketplace, or
distributed-runtime capability is out of scope.
