# v2 Architecture

## Intent

v2 scales orchestration from one page to projects and chapters while keeping the v1 page workflow as the source of truth for page-level safety. It adds extension points at application and infrastructure boundaries; it does not move workflow rules into delivery code, plugins, or providers.

## Bounded responsibilities

```text
Delivery: CLI / REST API / MCP Server / Web UI
                         |
Application: ProjectWorkflowEngine / ChapterWorkflowEngine / BatchWorkflowEngine
                         |
                 existing page WorkflowEngine
                         |
Domain: Project, Chapter, Page, page StateMachine, policies, events
                         |
Ports: Repository, EventBus, ImageGenerator, LLMProvider, Prompt stages
                         |
Infrastructure: local/DB repositories, memory/Redis/RabbitMQ buses,
                image and LLM providers, task workers, plugin hosts
```

Dependencies point inward. A delivery adapter translates input into an application request and translates typed results/errors out. Infrastructure implements ports. The domain imports neither transport, provider SDK, database, nor plugin-discovery code.

## Compatibility boundary

The current `WorkflowEngine` stays page-only and continues to own:

- determining the next permitted page state;
- selecting the eligible page agent;
- executing exactly that agent;
- updating the page context; and
- publishing page workflow events.

`Director` remains a coordinator/facade; it does not gain transition logic. New hierarchy engines compose page-engine invocations instead of replacing or subclassing its transition behaviour. Existing v1 calls therefore keep their meaning and return types.

## New planned application contracts

The following names are design targets unless stated otherwise. `PluginRegistry`
and its local lifecycle manager are implemented as Phase 11 outer-layer
components; they do not change the Page `WorkflowEngine`.

| Contract | Role | v1 relationship |
| --- | --- | --- |
| `ProjectWorkflowEngine` | coordinates chapters, project milestones, and project audit records | composes chapter engines |
| `ChapterWorkflowEngine` | sequences pages and continuity checkpoints within one chapter | composes page engines |
| `BatchWorkflowEngine` | schedules independent eligible page operations with bounded concurrency | delegates each page operation to `WorkflowEngine` |
| `WorkflowPolicy` | explicit, versioned policy for higher-level sequencing | cannot alter the v1 default policy implicitly |
| `PluginRegistry` | owns named extension registrations | implemented for local plugins; wraps existing factories rather than bypassing them |

## Aggregate and identity design

`Project` remains the root aggregate. A planned `Chapter` value/aggregate reference has a stable `chapter_id`, order, page references, metadata, and a chapter history. Pages retain a stable page number and a workflow history.

All externally submitted operations use a request ID and an idempotency key scoped to `(project_id, chapter_id?, page_number?, operation)`. Results record the initiating actor, policy version, plugin/provider identity, timestamps, and input/output artifact references. This permits safe retries without inventing a second transition.

## Concurrency model

Only work on different pages may run concurrently. A single page has an optimistic version (or equivalent repository compare-and-swap token). Its transition, artifacts, history entry, and published workflow event are committed as one logical operation. A stale write yields a typed conflict, not an automatic retry that can hide a human decision.

Project and chapter workflow engines may reserve work, but they cannot execute an ineligible page state. Cross-page operations such as continuity create advisory artifacts; they never mutate a page state directly.

## Event architecture

The existing `EventBus` remains the synchronous baseline. Durable buses use the same canonical event envelope plus fields for `event_id`, `schema_version`, `occurred_at`, `correlation_id`, `causation_id`, and aggregate identity.

At-least-once transports require idempotent consumers keyed by `event_id`. Transactional persistence and publication are a later design decision: an outbox is not assumed by v2, and must receive a separate review before it is introduced.

## Migration strategy

1. Add new contracts alongside v1 contracts, never by widening an existing method's required arguments.
2. Version serialized project documents and write explicit readers/migrations.
3. Publish contract tests that every first-party adapter and plugin must pass.
4. Deprecate only through a documented v2 minor release, with an adapter or a migration path.
5. Reserve breaking contract removals for a future major release.

## Architecture decisions still required before code

- Decide whether chapter membership is embedded in `Project` or stored as a separately versioned aggregate reference.
- Select a transaction/publication strategy before durable events and workers.
- Define a credential-secrets boundary for server, worker, and local CLI use.
