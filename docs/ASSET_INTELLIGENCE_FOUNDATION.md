# Asset Intelligence Foundation

Asset Intelligence is a repository-port projection, not an asset store or a new
repository implementation. It builds immutable Asset DTOs from known asset
keys in the selected Project and one-page workflow context.

Only asset category and metadata keys are emitted. Metadata values, prompts,
images, credentials, and other artifact payloads are redacted. The service
does not create relationships, perform external lookups, or write indexes.

Use `manga-director director asset-intelligence --project <id> --page <number>`
to inspect a report. FastAPI and MCP adapters expose the corresponding DTO only
when their optional Application providers are configured.

