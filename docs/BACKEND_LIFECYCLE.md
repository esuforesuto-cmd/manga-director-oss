# Image Backend Lifecycle

`ImageBackendRuntime` provides cached discovery, lifecycle snapshots, and metadata-only validation for registered image backends. `validate_preset()` and `validate_workflow()` inspect the backend metadata; they do not generate an image or contact a service.

Use `invalidate_cache()` after an intentional registry change. Backend lifecycle tracking uses the same `ready`, `healthy`, `degraded`, `unavailable`, and `shutdown` vocabulary as LLM providers while preserving the `ImageGenerator` protocol.
