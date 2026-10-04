# Migrating from v4.4 to v4.5.0

v4.5.0 is additive over v4.4. Existing projects, repositories, workflow state,
CLI scripts, FastAPI and REST integrations, MCP clients, Plugin and Extension
SDK consumers, Providers, Backends, and Web UI integrations continue to work
without changes.

## Upgrade

Install `manga-director==4.5.0` using the usual package process. No data,
database, configuration, or code migration is required.

## Optional Creative Intelligence Ecosystem DTOs

The new `manga_director.production` exports are optional, read-only DTO
services. They do not register or invoke a service, load or execute a plugin,
operate a marketplace, synchronize knowledge, establish federation networking,
apply governance, approve, enforce policy, monitor, alert, retry, recover, or
mutate workflow state. Existing applications do not need to adopt them.

## Safety invariants

The StateMachine remains authoritative: each execution covers exactly one Page,
workflow stages cannot be skipped, image generation requires a persisted
storyboard, and page approval requires a completed quality review.
