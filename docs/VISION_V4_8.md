# v4.8 Vision: Creative Operating System

## Vision

v4.8 defines the final integration design for a local-first **Creative
Operating System**. It organizes the existing Workspace, Agent Platform,
Knowledge, Production, Enterprise, and Decision Platform capabilities into a
coherent long-lived platform without replacing their public contracts or
changing the Core domain.

## Mission

Give creative teams one understandable model for project scope, evidence,
review, lifecycle, and operational insight while preserving the specialist
modules that already provide those capabilities. Consolidation means a shared
language and compatible composition boundaries—not a rewrite or removal.

## Design principles

- **Compatibility first:** v4.7 Python API, CLI, FastAPI, REST, MCP, Web UI,
  Repository, Workflow, Agent, Plugin, Extension SDK, Provider, and Backend
  contracts remain supported and canonical.
- **Core authority:** The domain StateMachine remains the source of truth. No
  platform layer can bypass transitions, skip a stage, or alter a Workflow.
- **One-page safety:** Every workflow-related view remains scoped to exactly
  one Page; image generation requires a persisted storyboard and approval
  requires a completed quality review.
- **Composable modules:** Modules publish caller-supplied, transport-neutral
  DTOs and evidence references. They do not acquire hidden runtime ownership.
- **Human-owned operations:** Planning, recommendation, lifecycle, and
  operational intelligence are advisory; a person retains approval and action
  responsibility.
- **Local and explainable:** No implicit Cloud service, data transfer,
  telemetry collection, automatic remediation, or autonomous execution is
  introduced.

## Platform pillars

| Pillar | v4.8 design outcome |
| --- | --- |
| Unified Creative Platform | A common project/evidence/review vocabulary across established modules. |
| Modular Runtime | Clear ownership, dependency direction, capability descriptions, and compatible composition rules. |
| Unified API Surface | A future additive facade and naming map that preserve all existing entry points. |
| Operational Intelligence | Read-only cross-domain summaries built from explicitly supplied evidence. |
| Lifecycle Management | A consistent reference model for project, creative, knowledge, decision, production, and release lifecycles. |

## Non-goals

This is a design-only cycle. v4.8 does not implement a Core Architecture
redesign, remove or rename public APIs, automate API migration, change
Repository interfaces, mutate or execute Workflows, dispatch Agents, generate
content, automatically approve or publish, add a Provider or Backend, create
a hosted platform, operate a marketplace, enable billing, or introduce a
distributed runtime.

## Migration commitment

No v4.7 consumer action is required by this planning cycle. Future work must
be additive, retain existing names and behavior, supply compatibility adapters
before any preferred facade, and use contract fixtures to prove that legacy and
consolidated views yield equivalent domain-safe evidence. Removal is outside
v4.8.

See the [architecture report](ARCHITECTURE_V4_8.md), [consolidation
roadmap](ROADMAP_V4_8.md), and [migration strategy](MIGRATION_V4_8.md).
