# v5.0 Architecture: One Creative Platform

## Architecture decision

One Creative Platform is an optional composition layer above existing module
owners. It is not a replacement runtime, persistence model, or workflow path.

```text
Python API | CLI | FastAPI/REST | MCP | Web UI | Extension SDK
                              |
                   Unified Creative API (optional)
                              |
                    Unified Creative Platform
       Context | Runtime facade | SDK facade | Compatibility adapters
                              |
 Workspace | Knowledge | Agents | Production | Enterprise | Decision | Ecosystem
                              |
 Project | Repository | WorkflowEngine | StateMachine | existing adapters
```

## Ownership and dependency direction

| Layer | v5 responsibility | Must not do |
| --- | --- | --- |
| Core domain | Retain Project/Page rules and legal state transitions. | Import unified platform concepts. |
| Existing module owners | Retain domain behavior, persistence, and public APIs. | Transfer source-of-truth ownership. |
| Unified Context | Reference caller-supplied scope and evidence consistently. | Persist, merge, synchronize, or infer source data. |
| Unified API | Offer opt-in, compatible composition endpoints. | Rename/remove legacy routes or alter transport behavior. |
| Unified Runtime | Describe module capability/dependency metadata. | Load, route, invoke, schedule, or replace services. |
| Unified SDK | Provide typed client-side composition helpers. | Hide workflow safeguards or mutate state. |

## Required workflow boundary

The existing StateMachine remains authoritative for every Page transition. A
unified request must retain one-Page scope, cannot skip a stage, cannot request
image generation without a persisted storyboard, cannot approve without a
completed quality review, and cannot accept a multi-page generation request.

## Consolidation sequence

1. Inventory duplicate vocabulary and public contracts.
2. Publish context and API envelopes as documentation and DTO designs.
3. Add opt-in facades only after equivalence fixtures prove legacy behavior is
   unchanged for identical supplied evidence.
4. Offer aggregate reports without central persistence, policy enforcement, or
   action routing.
5. Review deprecation only after an announced support window; no v5.0 removal
   is planned.

See [Unified Creative Platform](UNIFIED_CREATIVE_PLATFORM.md),
[Unified Context](UNIFIED_CONTEXT.md), [Unified API](UNIFIED_API.md),
[Unified Runtime](UNIFIED_RUNTIME.md), and [Unified SDK](UNIFIED_SDK.md).

