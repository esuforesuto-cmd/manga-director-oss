# Provider Lifecycle

`LLMProviderRuntime` adds an application-layer lifecycle around the unchanged `LLMProvider` protocol. It never invokes `generate()` while discovering or checking a provider.

The states are `ready`, `healthy`, `degraded`, `unavailable`, and `shutdown`. Call `initialize()` to register known providers, `health_snapshot()` for local construction checks, and `shutdown()` when the host is closing. A future provider may add remote probes without changing the core protocol.

Lifecycle state is diagnostic evidence, not workflow control flow. A workflow still follows the domain state machine.
