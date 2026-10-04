# v4.4.0 Compatibility Verification

v4.3 is the compatibility baseline. The stable v4.4 release preserves the
Python API, CLI, FastAPI/REST, MCP, Repository, Workflow, Plugin, Provider,
Backend, Web UI, and Extension SDK contracts. The new Enterprise Platform
services are additive and transport-neutral; no existing route, protocol,
interface, serialization format, or StateMachine transition changes.

The Enterprise end-to-end validation confirms a persisted one-page storyboard
survives save/reload while Enterprise reports remain non-executing. No migration
is required; see [Migration Guide](MIGRATION_V4_4.md).
