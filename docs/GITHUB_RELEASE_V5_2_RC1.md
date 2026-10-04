# GitHub Release Notes: v5.2.0 RC1

## Creative Automation Framework

v5.2.0 RC1 adds optional, local Automation Framework diagnostics: Automation
Engine, Rule Engine, Event Bus, Workflow Templates, Automation Registry,
Intelligence, Governance, Observability, Reliability, Lifecycle, and SDK
maturity reports.

## Compatibility

v5.0 LTS and v5.1 Python API, CLI, FastAPI/REST, MCP, Web UI, Repository,
Workflow, Extension SDK, Provider, and Backend contracts are preserved. No
migration is required and no existing caller must opt into Automation metadata.

## Safety

This RC does not execute an automation plan, dispatch an event, start a queue,
schedule work, mutate a workflow, enforce policy, collect telemetry, persist
automation state, recover components, self-learn, decide autonomously, or
approve a Page automatically.

See [RELEASE_V5_2_RC1.md](../RELEASE_V5_2_RC1.md) for validation evidence and
maintainer-controlled publication gates.
