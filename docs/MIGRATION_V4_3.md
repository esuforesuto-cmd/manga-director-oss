# Migrating from v4.2 to v4.3.0

v4.3.0 is additive over v4.2. Existing projects, repositories, workflow state,
CLI scripts, FastAPI and REST integrations, MCP clients, Extension SDK
consumers, Providers, Backends, and Web UI integrations continue to work
without changes.

## Upgrade

Install `manga-director==4.3.0` using the usual package process. No data,
database, configuration, or code migration is required.

## Optional Creative Production Platform DTOs

The new `manga_director.production` exports are optional, read-only DTO
services. They do not apply plans, start stages, persist assets, assign tasks,
create artifacts, export, publish, distribute, approve, enforce policy,
monitor, alert, retry, recover, or mutate workflow state. Existing
applications do not need to adopt them.

## Safety invariants

The StateMachine remains authoritative: each execution covers exactly one Page,
workflow stages cannot be skipped, image generation requires a persisted
storyboard, and page approval requires a completed quality review.
