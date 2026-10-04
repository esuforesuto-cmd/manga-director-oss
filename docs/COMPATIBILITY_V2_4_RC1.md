# v2.4.0 RC1 Compatibility Audit

## Scope and method

This audit compares documented v1.x, v2.0.x, v2.1.x, v2.2.x, and v2.3.x
contracts against `2.4.0rc1`. It combines public-export, architecture/import,
release-contract, CLI/MCP, repository/integrity, production/reliability, and
documentation-link tests with manual dependency-direction review.

| Surface | v2.4.0rc1 result |
| --- | --- |
| Python API | Root `Director`, `WorkflowEngine`, `WorkflowContext`, `Project`, `Page`, `ImageGenerator`, `Repository`, DTOs, and documented errors are retained. |
| Page workflow | Exactly one page, forward-only StateMachine transitions, persisted storyboard before generation, quality-before-approval, and explicit approval are retained. |
| CLI | Existing workflow, project, chapter, batch, plugin, MCP, diagnostics, health, and database commands are retained. |
| MCP / FastAPI | MCP stays local DTO JSON-RPC; the optional FastAPI adapter remains observability DTO-only. Package-derived version remains aligned. |
| Repository | The `load`, `save`, `exists`, `delete`, `list` port is unchanged; recovery, integrity, history, and operations helpers remain additive. |
| Plugin / Extension SDK | Registry, manifest, lifecycle, compatibility, context, and packaging contracts are unchanged. |
| Provider / Image Backend | Factory/Protocol contracts and provider-neutral Agent behavior are unchanged; inventory and health reports are diagnostic-only. |
| Automation / Notification / Web UI | Existing outer delivery boundaries remain unchanged and do not acquire Core imports. |

## Versioning

Python package metadata, root import, MCP initialization, optional OpenAPI
metadata, and SBOM use `2.4.0rc1`. The independent npm frontend uses the
equivalent valid npm prerelease form `2.4.0-rc.1`.

## Conclusion

No breaking change was identified. RC feedback is restricted to corrective
release work; new workflow, provider, backend, cloud, marketplace, or
distributed-runtime work is out of scope.
