# v5.5 Vision: Creative Platform Lifecycle

## Vision update

v5.5 defines the **Creative Platform Lifecycle**: a common, human-owned way to describe how platform capabilities are introduced, supported, upgraded, deprecated, measured, and eventually retired. The goal is predictable long-term maintenance, not a new execution engine.

## Product mission

Make platform evolution understandable before it is operational. Maintainers, extension authors, and production teams should be able to identify supported versions, upgrade evidence, deprecation commitments, and health signals without guesswork or automatic platform action.

## Design principles

- **LTS compatibility first.** v5.0 LTS contracts remain usable throughout the v5.5 development cycle.
- **Compatibility is explicit.** Upgrade and deprecation decisions have an owner, scope, evidence, notice, and rollback guidance.
- **Human-controlled evolution.** Reports inform a maintainer; they do not apply upgrades, remove capabilities, or change configuration.
- **Read-only health.** Health is a normalized observation, never an automatic repair, alert dispatch, or operational command.
- **Core ownership is unchanged.** The StateMachine, WorkflowEngine, repositories, Runtime, SDK, and existing public surfaces retain ownership.

## Non-goals

v5.5 does not add automatic upgrades, feature removal, policy enforcement, telemetry collection, monitoring agents, runtime repair, workflow mutation, provider or backend changes, Cloud services, or a Core Architecture rewrite.

## Migration strategy

v5.4.0 is the stable baseline. Future lifecycle metadata and reports are optional, presentation-neutral, and additive. Existing callers retain their current API, CLI, FastAPI/REST, MCP, Web UI, Repository, Workflow, and SDK contracts. See [the v5.5 migration strategy](MIGRATION_V5_4_TO_V5_5.md).
