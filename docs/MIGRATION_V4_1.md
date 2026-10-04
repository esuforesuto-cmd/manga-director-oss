# Migrating from v4.0 to v4.1.0

v4.1.0 is additive over v4.0. Existing projects, repositories, workflow state,
CLI scripts, FastAPI integrations, MCP clients, extension SDK consumers,
Providers, Backends, and Web UI integrations continue to work without changes.

## Upgrade

Install `manga-director==4.1.0` using your normal package process. No project or
database migration is required.

## Optional Multi-Agent DTOs

The new `manga_director.production` exports are optional DTO services. They do
not invoke agents, dispatch tasks, send messages, persist history, enforce
policy, transition workflow state, complete review, or approve pages. Existing
applications do not need to adopt them.

## Safety invariants

The StateMachine remains authoritative: every execution concerns exactly one
Page, workflow stages cannot be skipped, image generation requires a persisted
storyboard, and page approval requires completed quality review.
