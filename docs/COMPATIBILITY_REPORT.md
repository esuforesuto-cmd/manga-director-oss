# v5.6 Compatibility Report

v5.6.0 RC1 is additive. It exposes new `manga_director.production` report DTOs
and services without changing existing public imports, CLI commands,
FastAPI/REST routes, MCP tools, Web UI contracts, repository interfaces, SDK
contracts, or workflow transitions.

The Engine modules import only the existing workflow contracts, `PageState`,
and Application-layer DTO base. They do not import delivery adapters,
repositories, or a workflow engine, and they do not call transition, save, or
execution methods. Existing callers can omit all v5.6 metadata and services.
