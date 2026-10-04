# Migrating from v4.1 to v4.2.0

v4.2.0 is additive over v4.1. Existing projects, repositories, workflow state,
CLI scripts, FastAPI integrations, MCP clients, extension SDK consumers,
Providers, Backends, and Web UI integrations continue to work without changes.

## Upgrade

Install `manga-director==4.2.0` using your normal package process. No project,
database, or configuration migration is required.

## Optional Autonomous Creative System DTOs

The new `manga_director.production` exports are optional DTO services. They do
not start execution sessions, dispatch tasks, persist checkpoints, resume work,
invoke models, create artifacts, generate images, apply plans, start pipelines,
approve pages, enforce policy, export telemetry, retry, recover, or mutate
workflow state. Existing applications do not need to adopt them.

## Safety invariants

The StateMachine remains authoritative: every execution concerns exactly one
Page, workflow stages cannot be skipped, image generation requires a persisted
storyboard, and page approval requires completed quality review.
