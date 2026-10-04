# v6.0 SDK v1.0 Reference

## Frozen SDK surface

`SDKCapabilityDTO` describes a compatible `python`, `cli`, `fastapi`, `mcp`,
or `web_ui` surface by identifier and source reference. `SDKFoundationReport`
returns the sorted descriptors, unique surface count, compatibility result, and
explicitly false publication and public-API-change flags.

## Compatibility

The SDK Foundation is additive to existing Python, CLI, FastAPI/REST, MCP,
Web UI, Plugin, and Extension SDK contracts. It neither generates nor
publishes an SDK, and it creates no endpoint, command, protocol, or browser
contract.

## Stability boundary

SDK descriptors are observational. Existing SDK authors retain their current
imports and interfaces; no migration, package rebuild, or runtime registration
is required to adopt v6.0 reports.
