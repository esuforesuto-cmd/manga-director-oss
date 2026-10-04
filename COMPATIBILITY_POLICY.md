# Compatibility Policy

## Guaranteed surfaces

The active v6.x LTS line preserves v5.x Python API, CLI, FastAPI/REST, MCP,
Web UI, Repository, Workflow, SDK, Plugin, and StateMachine contracts. It also
preserves the frozen v6.0 Platform API v1.0, SDK v1.0, Extension API v1.0, and
Marketplace Specification v1.0.

## Behavioral guarantees

Maintenance changes are additive or corrective. They must not bypass
StateMachine transition validation, process more than one Page in a workflow
execution, generate an image before storyboard persistence, or approve a Page
without completed quality review.

## Change control

Any proposed incompatible change requires an RFC, a migration strategy, and a
future major-version decision. See [RFC_PROCESS.md](RFC_PROCESS.md) and
[DEPRECATION_POLICY.md](DEPRECATION_POLICY.md).
