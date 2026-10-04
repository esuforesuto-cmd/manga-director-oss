# Migrating from v4.6 to v4.7.0

v4.7.0 is additive over v4.6. Existing projects, repositories, workflow state,
CLI scripts, FastAPI and REST integrations, MCP clients, Agent Platform,
Plugin and Extension SDK consumers, Providers, Backends, and Web UI
integrations continue to work without changes.

## Upgrade

Install `manga-director==4.7.0` using the usual package process. No data,
database, configuration, or code migration is required.

## Optional Creative Decision Platform DTOs

The new `manga_director.production` exports are optional, read-only DTO
services. They do not collect or persist evidence, select a decision or
recommendation, complete review, grant approval, enforce policy, mutate or
execute a workflow, monitor, alert, retry, recover, or call an external
service. Existing applications do not need to adopt them.

## Safety invariants

The StateMachine remains authoritative: each execution covers exactly one Page,
workflow stages cannot be skipped, image generation requires a persisted
storyboard, and page approval requires a completed quality review.
