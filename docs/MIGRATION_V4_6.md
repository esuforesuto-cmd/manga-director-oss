# Migrating from v4.5 to v4.6.0

v4.6.0 is additive over v4.5. Existing projects, repositories, workflow state,
CLI scripts, FastAPI and REST integrations, MCP clients, Agent Platform,
Plugin and Extension SDK consumers, Providers, Backends, and Web UI
integrations continue to work without changes.

## Upgrade

Install `manga-director==4.6.0` using the usual package process. No data,
database, configuration, or code migration is required.

## Optional Creative Intelligence OS DTOs

The new `manga_director.production` exports are optional, read-only DTO
services. They do not collect or persist context, access or synchronize memory,
update a model, learn, invoke an agent, make an autonomous decision, mutate or
execute a workflow, apply governance, approve, monitor, alert, retry, recover,
or call an external service. Existing applications do not need to adopt them.

## Safety invariants

The StateMachine remains authoritative: each execution covers exactly one Page,
workflow stages cannot be skipped, image generation requires a persisted
storyboard, and page approval requires a completed quality review.
