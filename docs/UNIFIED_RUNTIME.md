# Unified Runtime

## Purpose

Unified Runtime is a design for describing the existing modular system. It is
not an executable runtime manager. Its only future role is to expose declared
module capabilities, ownership, dependencies, and compatibility status.

## Module descriptor

A future descriptor may contain `module_id`, `owner_layer`, `capabilities`,
`public_surfaces`, `depends_on`, `source_of_truth`, `compatibility_level`, and
`human_review_required`. Descriptors are static, local, and supplied by their
owners.

## Runtime constraints

- No dynamic discovery, import, loading, instantiation, activation, routing,
  scheduling, delegation, execution, permission grant, or replacement.
- No change to existing Providers, Backends, Plugin execution, or Extension
  SDK lifecycle.
- Core has no dependency on a descriptor or facade.
- A descriptor cannot assert health, collect telemetry, perform a probe, or
  recover a failed operation.

## Modular consolidation map

| Existing module family | Future runtime position | Owner retained |
| --- | --- | --- |
| Workspace / Enterprise | Collaboration and portfolio descriptors. | Application owners. |
| Knowledge / Context | Knowledge and evidence descriptors. | Knowledge owners. |
| Agent / Decision | Planning, review, approval-readiness descriptors. | Application owners. |
| Production / Ecosystem | Production and ecosystem descriptors. | Production owners. |
| Workflow / Core | Protected workflow authority descriptor. | Core StateMachine. |

