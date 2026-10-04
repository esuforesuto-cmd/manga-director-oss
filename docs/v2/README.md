# v2 Design Blueprint

> Status: the local Plugin System, LLM Adapter, Prompt Pipeline, and sequential
> Project/Chapter workflow hierarchy described here are implemented in Phases
> 11 through 15. Sequential Batch orchestration is implemented. The local MCP
> stdio delivery adapter is implemented in Phase 17 and the minimal Web UI in
> Phase 18. Remote/platform areas and parallel Batch remain design-only and do
> not alter the v1.0.0 page workflow or public API.

This blueprint defines how `manga-director` can grow beyond a single-page workflow without weakening the v1 safety model. It is an input to future design reviews, not an implementation plan that has already been accepted.

## Non-negotiable compatibility rules

1. `Director`, `WorkflowEngine`, `WorkflowContext`, `Project`, `Page`, `ImageGenerator`, and `Repository` remain importable from `manga_director` throughout v2.x.
2. The existing `WorkflowEngine` remains the page-only engine. Its fixed states and forward-only transitions remain the default page policy.
3. Human approval remains explicit. A batch, API, or plugin cannot silently approve a page.
4. Existing `ProjectRepository` and `ImageGenerator` contracts remain valid. Broader contracts are introduced as opt-in sibling ports and adapters.
5. All persisted projects carry a schema version before a new persisted field becomes required. Migrations must be explicit and reversible where possible.

## Design documents

| Document | Decision area |
| --- | --- |
| [Architecture](ARCHITECTURE.md) | boundaries, dependency direction, compatibility, and staged adoption |
| [Plugins](PLUGINS.md) | versioned extension points and registry ownership |
| [Workflows](WORKFLOWS.md) | Project / Chapter / Page / Step hierarchy and batch execution |
| [API and clients](API.md) | REST, MCP server, and React/Next.js screen contracts |
| [Prompt pipeline](PROMPT_PIPELINE.md) | typed prompt stages while retaining Markdown templates |
| [LLM adapters](LLM_ADAPTERS.md) | provider-neutral LLM boundary and capability model |
| [Image, persistence, and execution](PLATFORM_ADAPTERS.md) | image evolution, databases, event buses, and workers |

## Review gate before implementation

Each proposed v2 feature must pass these questions before code is started:

- Which existing v1 contract does it preserve, adapt, or deprecate?
- Is it a domain rule, an application orchestration concern, or an outer adapter?
- What is its idempotency key, error model, audit trail, and migration path?
- Can it preserve per-page validation and explicit approval under concurrency?
- Does it need a new versioned extension contract rather than a change to a v1 protocol?

## Proposed delivery order

1. Define project schema versioning, plugin API versioning, and contract tests.
2. Add persistence and durable event adapters behind ports.
3. Add hierarchy and batch orchestration while retaining the page engine.
4. Add REST/MCP delivery adapters and the web client over those application APIs.
5. Add optional plugin loading only after the registry and isolation policy are tested.

No item in this document authorizes an implementation by itself.
