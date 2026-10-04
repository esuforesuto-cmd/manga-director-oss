# Provider Management

`ProviderManagement` produces a local, provider-neutral inventory from the
existing `LLMProviderRuntime`. Its report includes registered metadata,
capabilities, declared priority ordering, construction health, and a diagnostic
recommendation. It never selects a Provider for an Agent, changes factory
registrations, sends an LLM request, or invokes a fallback.

`priorities` is a per-report diagnostic override. It is useful to inspect a
proposed ordering while leaving the registered Factory unchanged. The
recommendation is informational only. Fallback execution remains deliberately
unimplemented.

Call `record_health()` with a `HealthHistoryStore` and a Project ID to persist a
bounded provider availability snapshot through `ProjectRepository`.
