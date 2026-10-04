# v2 Design Roadmap

This document describes v2 candidates only. It authorizes no implementation and does not change v1.0.0 behavior.

The reviewed Phase 10 design blueprint is in [docs/v2/README.md](v2/README.md). It defines the compatibility rules and detailed boundaries for each candidate; this document remains the high-level roadmap.

Phase 11 implements the local Plugin System portion of that blueprint. Its
manifest, lifecycle, registry, examples, and CLI are documented in
[docs/plugins](plugins/plugin_api.md); no other roadmap candidate is enabled by
that implementation.

## Design principles

- Preserve the current Clean Architecture dependency direction.
- Keep `StateMachine` as the authority for workflow legality.
- Keep agents stateless and image providers behind `ImageGenerator`.
- Add capabilities through ports and adapters, not delivery-layer conditionals.
- Preserve explicit human approval and one-page workflow safety unless a separately designed policy changes it.

## Candidate capabilities

| Candidate | Design direction | v1 compatibility consideration |
| --- | --- | --- |
| FastAPI | Add a delivery adapter that translates HTTP requests to existing application services. | No domain or agent HTTP imports. |
| Plugin system | Discover optional adapters through a versioned registration contract. | Keep built-ins available without plugins. |
| MCP | Expose safe Project and workflow operations through an MCP delivery adapter. | Reuse Director/WorkflowEngine; do not bypass transitions. |
| Redis EventBus | Implement the existing EventBus contract with Redis transport. | Preserve event schema and in-process behavior for tests. |
| RabbitMQ | Add durable event publication through an adapter and delivery policy. | Avoid domain dependencies on broker clients. |
| Celery | Add optional task dispatch for long-running adapter calls. | Preserve deterministic state and idempotency boundaries. |
| Database repository | Implement `ProjectRepository` with migrations and concurrency control. | Define schema versioning before production use. |
| Web UI | Build a client over API/application services, not the domain directly. | Keep workflow validation server-side. |
| Multi-provider controls | Extend Factory configuration with provider capabilities and safe selection policy. | Keep ImageAgent provider-agnostic. |
| Batch workflow | Introduce a separately validated orchestration policy. | Do not weaken one-page invariants by default. |
| Multi-page workflow | Design a chapter-level aggregate and continuity transaction model. | Maintain page-level audit history and approval. |

## Proposed sequencing

1. Define project schema versioning and migration policy.
2. Add database persistence and durable event adapters behind existing protocols.
3. Add FastAPI and authenticated delivery concerns as separate adapters.
4. Add plugin/MCP integrations only after versioned extension contracts are reviewed.
5. Design batch and multi-page workflows as explicit new state-machine policies.
