# Service Discovery

## v6.0 Iteration 2 foundation

Service Discovery presents a sorted inventory of caller-supplied Service
Registry references and flags duplicate identifiers. It does not inspect a
runtime, register services, instantiate extensions, call plugins, or mutate a
registry.

## Compatibility

The inventory is an opt-in, read-only Application-layer report. Existing
Platform Core, Service Registry, Plugin Runtime, SDK, CLI, FastAPI, MCP, and
Web UI contracts remain unchanged.
