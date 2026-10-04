# v2.1.0 RC1 Compatibility Audit

## Baseline and method

The published v2.0 root API contract in `docs/PUBLIC_API.md`, the v2.0 release
assets, and the repository's contract tests are the compatibility baseline.
This checkout does not contain a Git tag object for an automated binary diff,
so the audit compares the documented contract and executable public entry
points directly.

## Result

| Surface | v2.0 contract | v2.1.0rc1 result |
| --- | --- | --- |
| Python root API | `Director`, `WorkflowEngine`, `WorkflowContext`, `Project`, `Page`, ports, DTOs, typed errors | Preserved; `__version__` is additionally exported for standard introspection. |
| Page workflow | Forward-only Draft → Approved with explicit approval | Preserved and covered by state/workflow contract tests. |
| Project/Chapter/Batch | One page per Page-engine invocation | Preserved; sequential execution only. |
| CLI | Existing command and group names | Preserved; installed-wheel smoke verifies help, MCP, and Plugin groups. |
| MCP | Local stdio JSON-RPC and `McpToolResult` DTO | Preserved; server metadata now reports the package version. |
| Errors and DTOs | Typed domain errors; no raw mutable aggregate output | Preserved. Unexpected MCP transport errors are more safely masked. |
| Plugin / Extension | Local manifest and SDK contracts | Preserved; wheel packaging and SDK RC-version validation are covered. |
| Repository / migrations | Repository port and SQLite/Alembic initial migration | Preserved; migration smoke passed. |
| FastAPI / REST API | Not shipped in this source baseline | Still not shipped; no compatibility claim is made. |
| Web UI API | Typed client for a separately compatible HTTP service | Client remains presentation-only; no backend contract is implied. |
| Automation | Not shipped in this source baseline | Still not shipped; no compatibility claim is made. |

## Compatibility conclusion

No documented v2.0 public Python, CLI, MCP, workflow, persistence, or adapter
contract was removed or renamed. The only public addition is `__version__`.
RC1 therefore remains backward compatible for shipped surfaces. FastAPI/REST
and Automation cannot be compared as shipped APIs because they are absent in
both the v2.0 maintenance baseline and RC1 source.
