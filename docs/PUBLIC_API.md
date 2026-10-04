# Public API Contract

This document defines the supported public surface for stable `6.0.0` and the
active `6.0.x` LTS maintenance line. The v6.0 public contract retains the
documented v5.x compatibility surfaces; older version records are historical
references, not the current compatibility authority. Import from `manga_director`
whenever possible; subpackages are
implementation detail unless a document explicitly names them as an extension
contract.

## Python

The root package exports the following stable types:

| Area | Public names |
| --- | --- |
| Workflow | `Director`, `WorkflowEngine`, `WorkflowContext` |
| Domain | `Project`, `Page` |
| Ports | `ImageGenerator`, `Repository`, `LLMProvider` |
| Result DTOs | `ImageResult`, `LLMResult`, `PromptRequest`, `PromptResponse` |
| Errors | `MangaDirectorError`, `WorkflowError`, `StateTransitionError`, `RepositoryError`, `ConfigurationError`, `ImageGeneratorError`, `ValidationError`, `CLIError` |

All root exports are typed. `Director` is a coordinator facade only;
`WorkflowEngine` and `StateMachine` remain responsible for legal transitions.
No root exports are deprecated in this maintenance iteration.

`manga_director.sdk` is a separate, documented extension contract. Its base
classes and manifest types are public to extension authors. Other subpackages
must not be imported by ordinary application code unless their specific
extension document says so.

## CLI

The supported executable is `manga-director`. Use `manga-director --help` as
the canonical command schema. Primary page operations are `design`, `review`,
`storyboard`, `prompt`, `generate`, `quality`, and `approve`; `dialogue` and
`continuity` are non-transition support operations. `run` stops at
`QualityChecked`; only `approve` may move a page to `Approved`.

Project, chapter, batch, MCP, and plugin command groups are public delivery
surfaces. Their output is JSON DTO data, not mutable Domain objects.
`project status` and MCP `get_project_status` preserve their existing inputs
and fields and add a read-only `page_readiness` list. Each entry reports a
persisted Page's state, unmet cumulative prerequisites, one next operation (or
an explicit no-op), and `non_execution: true`; it does not authorize or run
that operation.

These status responses also add `readiness_summary` with
`completed_page_count`, `actionable_page_count`, `blocked_page_count`, and
`next_actionable_page_number`, plus `first_blocked_page` and
`next_actionable_page`. The counts partition
the existing `page_readiness` list: terminal no-ops are completed, blocked
no-ops are blocked, and StateMachine commands are actionable. The next page is
the smallest actionable page number, or `null` when none exists. When no page
is actionable, `first_blocked_page` is the lowest-numbered existing blocked
inspection (including its unmet prerequisites); otherwise it is `null`.
`next_actionable_page` is the first actionable inspection from the existing
ordered `page_readiness` list, or `null` for empty, all-terminal, or all-blocked
projects. Its `page_number` equals `next_actionable_page_number`, and its existing
state, operation, prerequisites, and `non_execution: true` are preserved without
a new decision or execution authorization. This additive optional DTO field
defaults to `None` when omitted from existing summary construction and is passed
through identically by generic, LocalFile, CLI, and MCP status paths.
The additive optional `readiness_outcome` field accepts `EMPTY`, `ACTIONABLE`,
`BLOCKED`, or `COMPLETE`, and defaults to `None` for existing summary construction.
Status always supplies one of these values from existing inspections/counts:
zero pages are `EMPTY`; any actionable Page makes the result `ACTIONABLE`, even
when blocked pages coexist; otherwise any blocked Page makes it `BLOCKED`,
including completed-plus-blocked projects; non-empty all-terminal projects are
`COMPLETE`. The outcome adds no execution authorization, persistence, Provider
construction, or changes to counts, pointers, Page ordering, commands, or tools.
Existing `current_page` semantics are unchanged.
The additive optional `readiness_focus_page` defaults to `None` when omitted from
existing summary construction. Status projects the existing outcome only:
`ACTIONABLE` exposes `next_actionable_page`, `BLOCKED` exposes `first_blocked_page`,
and `EMPTY` or `COMPLETE` exposes `null`. Generic, LocalFile, CLI, and MCP status
paths expose the same inspection with no new precedence or readiness decision.
This projection preserves counts, both pointers, Page ordering, and `current_page`,
and adds no persistence, Provider construction, or execution authorization.
An empty Project returns zero counts and a `null` next page. This immutable
summary does not persist data or execute work. Existing ProjectContext
construction remains valid; contexts without a readiness inspection default
`readiness_summary` to `null`. No root export, command, or MCP tool is added.

## MCP

The shipped MCP surface is local stdio JSON-RPC. `McpToolResult` contains
`success`, `operation`, `state`, `data`, `messages`, `errors`, and `metadata`.
Tool inputs are validated by the registry and do not bypass the page engine.
The MCP `serverInfo.version` is aligned with the package version.

## FastAPI and Web API

The optional `manga-director[api]` adapter exposes only health and diagnostics
DTO routes: `/health`, `/health/providers`, `/health/backends`, `/diagnostics`,
and `/repository/check`. Its OpenAPI version is derived from the package's
single Python version source. It does not expose workflow operations or Domain
models. The `web/` Next.js application remains an independent presentation
scaffold and requires a separately compatible workflow HTTP service.

## Compatibility rules

Maintenance changes must not rename public root exports, change legal workflow
transitions, add implicit approval, alter persisted project semantics, or make
adapters/provider selection visible to Agents. The POST-v6.1 I01–I06 readiness
DTO additions are verified pre-release work and do not change the stable 6.0.0
release claim. New public APIs require an architecture decision, a migration
note, and explicit release authorization.
