# v2 Platform Adapter Design

## Image adapter expansion

The v1 `ImageGenerator.generate(prompt) -> ImageResult` port remains valid. For richer providers, v2 adds an opt-in sibling request/result contract rather than breaking that simple interface:

```text
ImageGenerationRequest -> ExtendedImageGenerator -> ImageGenerationResult
```

The request can carry a rendered prompt reference, negative prompt, dimensions, seed, style references, output policy, idempotency key, and trace metadata. The result can carry artifact references, provider job ID, safety/status information, elapsed time, and messages. Capability declarations make optional features explicit. A compatibility adapter converts a simple v1 prompt to the extended request only when a provider supports it.

`ImageAgent` continues to receive an image-generation port, never a provider name. Provider choice stays in the composition root/selection policy. Async provider jobs are represented as application-level operations and do not update a page until their final typed result passes the page engine's normal command path.

## Repository evolution

`ProjectRepository` remains the stable minimum port. SQLite, PostgreSQL, and MongoDB implementations are future infrastructure adapters. A new versioned repository capability may add transactions, compare-and-swap revisions, pagination, and queries without changing required v1 methods.

| Store | Intended use | Required design concern |
| --- | --- | --- |
| SQLite | local/single-user projects | migrations, file locking, backup/export |
| PostgreSQL | shared/server deployment | transactions, row versioning, tenant boundary |
| MongoDB | document-oriented/project artifact workloads | document schema versions, indexes, consistency boundaries |

Project serialization gets a mandatory `schema_version`. Migration runs before validation, produces an audit record, and leaves an exportable backup. Storage adapters own mapping and transactions only; they do not own workflow decisions.

## Event bus evolution

`MemoryEventBus` remains the default. Redis and RabbitMQ adapters implement a versioned event envelope and explicitly declare delivery semantics, ordering scope, retry handling, dead-letter policy, and payload-size/artifact-reference policy. Consumers are idempotent by event ID. Broker libraries remain outside domain and workflow modules.

## Celery worker target

Celery is a possible infrastructure dispatcher for long-running image or LLM operations. Tasks carry an operation ID and expected page revision, invoke an application service, and return a typed result. They do not call agents or edit repositories outside the application command boundary. Retry/cancellation and task result retention need a separate operational policy.

## Operational observability

Every request, batch item, task, and event shares a correlation ID. Metrics cover transition conflicts, queue latency, provider latency/failure, retry counts, and approval lead time. Logs redact secrets and large prompt/image payloads; artifacts are referenced by stable IDs rather than embedded in events.
