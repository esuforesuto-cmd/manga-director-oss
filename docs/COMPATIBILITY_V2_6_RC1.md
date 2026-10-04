# v2.6.0 RC1 Compatibility Audit

## Scope and method

This audit compares documented v1.x and v2.0.x-v2.5.x contracts with
`2.6.0rc1`. It combines root-export, architecture/import, release-contract,
CLI/MCP/FastAPI, repository, workflow, planning, diagnostics, health, security,
and documentation-link tests with a manual dependency-direction review.

| Surface | v2.6.0rc1 result |
| --- | --- |
| Python API | Root `Director`, `WorkflowEngine`, `WorkflowContext`, `Project`, `Page`, `ImageGenerator`, `Repository`, DTOs, and documented errors are retained. |
| Page workflow | Exactly one page, forward-only StateMachine transitions, persisted storyboard before generation, quality-before-approval, and explicit approval are retained. |
| CLI | Existing workflow, project, chapter, batch, plugin, MCP, diagnostics, health, database, security, planning, analytics, and assurance commands are retained. |
| FastAPI / REST / MCP | FastAPI remains DTO-only delivery; MCP remains local DTO JSON-RPC. Their version metadata derives from the canonical package source. |
| Repository | The `load`, `save`, `exists`, `delete`, `list` port is unchanged; maintenance, integrity, planning, and readiness helpers are additive. |
| Plugin / Extension SDK | Registry, manifest, lifecycle, compatibility, context, and packaging contracts are unchanged. |
| Provider / Image Backend | Factory and Protocol contracts remain unchanged; selection, governance, and diagnostics are metadata-only additions. |
| Automation / Notification / Web UI | Existing outer delivery boundaries remain unchanged and do not acquire Core imports. |
| Diagnostics / Health / Reporting | Existing DTOs are retained; planning, analysis, governance, and readiness DTOs are optional additions under `manga_director.production`. |

## Versioning

Python package metadata, root import, MCP initialization, optional OpenAPI
metadata, and SBOM use `2.6.0rc1`. The independent npm frontend uses the valid
equivalent `2.6.0-rc.1`.

## Conclusion

No breaking change was identified. RC feedback is restricted to corrective
release work; new workflow, provider, backend, cloud, marketplace, distributed,
or autonomous-AI capability is out of scope.
