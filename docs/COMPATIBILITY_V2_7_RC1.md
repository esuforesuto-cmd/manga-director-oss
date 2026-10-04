# v2.7.0 RC1 Compatibility Audit

## Scope and method

This audit compares documented v1.x and v2.0.x-v2.6.x contracts with
`2.7.0rc1`. It combines root-export, architecture/import, release-contract,
CLI/MCP/FastAPI, repository, workflow, planning, Director, Knowledge,
diagnostics, health, security, and documentation-link tests with a manual
dependency-direction review.

| Surface | v2.7.0rc1 result |
| --- | --- |
| Python API | Root `Director`, `WorkflowEngine`, `WorkflowContext`, `Project`, `Page`, `ImageGenerator`, `Repository`, DTOs, and documented errors are retained. |
| Page workflow | Exactly one page, forward-only StateMachine transitions, persisted storyboard before generation, quality-before-approval, and explicit approval are retained. |
| CLI | Existing workflow, project, chapter, batch, plugin, MCP, diagnostics, health, database, security, planning, analytics, assurance, and Director commands are retained. |
| FastAPI / REST / MCP | FastAPI remains DTO-only delivery; MCP remains local DTO JSON-RPC. Version metadata derives from the canonical package source. |
| Repository / Knowledge | The `load`, `save`, `exists`, `delete`, `list` port is unchanged; Knowledge projections are additive, repository-derived, redacted, and non-mutating. |
| Planning / Diagnostics / Reporting | Existing contracts remain; Director, Knowledge, readiness, diagnostic, and dashboard DTOs are additive under `manga_director.production`. |
| Plugin / Extension SDK | Registry, manifest, lifecycle, compatibility, context, and packaging contracts are unchanged. |
| Provider / Image Backend | Factory and Protocol contracts remain unchanged; all v2.7 reports are local metadata and context analysis only. |
| Automation / Notification / Web UI / Health | Existing outer delivery boundaries remain unchanged and do not acquire Core imports. |

## Versioning

`pyproject.toml` retains its dynamic Hatch configuration to prevent duplicate
version management. Python package metadata, root import, MCP initialization,
optional OpenAPI metadata, and SBOM use `2.7.0rc1`. The independent npm
frontend uses the valid equivalent `2.7.0-rc.1`.

## Conclusion

No breaking change was identified. RC feedback is restricted to corrective
release work; new workflow, provider, backend, cloud, marketplace,
distributed-runtime, or autonomous-AI capability is out of scope.
