# Unified API Surface

`UnifiedApiSurfaceService` provides an opt-in read-only facade over the v5
gateway foundation. It reports the requested public surfaces and a static
Unified Registry descriptor while preserving Python, CLI, FastAPI/REST, MCP,
and Web UI contracts unchanged.

The registry accepts caller-supplied metadata only. It cannot discover, load,
invoke, route, schedule, activate, or replace a service. The API Surface adds
no HTTP route, OpenAPI change, CLI command, MCP tool, or Web UI dependency.

