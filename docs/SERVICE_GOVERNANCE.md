# Service Governance

## Scope

`service_governance()` turns the advisory v4.8 Service Orchestration report
into governance metadata. It retains explicit service ids and requires public
contract preservation plus human review.

## Boundary

This is not an access-control, capability, or execution system. It cannot
discover, load, instantiate, invoke, route, delegate, schedule, activate, or
replace a service; grant a permission; enforce a policy; or alter the existing
Runtime, Plugin/Extension SDK, Provider, Backend, CLI, FastAPI, MCP, or Web UI
contracts.
