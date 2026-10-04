# Unified Creative API

## Objective

The Unified Creative API is a future optional facade over established APIs. It
simplifies discovery and report composition while preserving all legacy names,
schemas, routes, flags, payloads, response semantics, and exit contracts.

## Surface design

| Surface | v5 design | Preservation requirement |
| --- | --- | --- |
| Python | Typed `UnifiedCreativePlatform` facade with explicit dependencies. | Existing imports and services remain canonical. |
| CLI | Optional read-only platform summary/diagnostic commands. | No existing command or output changes. |
| FastAPI / REST | Additive version-neutral report routes with existing DTO semantics. | Existing routes and OpenAPI schemas remain valid. |
| MCP | Additive diagnostic tools returning supplied-evidence reports. | Existing tools and JSON-RPC behavior remain valid. |
| Web UI | Optional composed dashboard view models. | Existing UI API client contracts remain valid. |

## Contract rules

1. Facade inputs accept existing DTOs and identifiers; they do not introduce a
   replacement Project, Page, Repository, or workflow command.
2. New fields are optional and safely ignorable by older consumers.
3. The facade returns immutable reports, never action commands or authority
   tokens.
4. Each facade endpoint has an equivalence fixture demonstrating that legacy
   behavior is unchanged for the same evidence.
5. No `/v1` or current route is repurposed; any future route is additive.

## API consolidation plan

| Phase | Deliverable | Exit evidence |
| --- | --- | --- |
| Inventory | Public API catalogue and duplicate-vocabulary map. | Contract fixtures for Python, CLI, REST, MCP, and Web UI. |
| Envelope | Additive scope/evidence/report DTO design. | Schema compatibility review. |
| Facade | Opt-in read-only composition service. | Legacy/facade equivalence tests. |
| Transport | Additive transport adapters only where needed. | OpenAPI/MCP/CLI/Web UI regression tests. |
| Review | Deprecation decision record after a support window. | No removal is admitted by v5.0. |

