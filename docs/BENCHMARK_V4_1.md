# v4.1.0 Benchmark Verification

Provider-free micro-benchmarks cover Agent Runtime, Orchestration, Collaboration
Workflow, Observability/Event processing, and Repository-adjacent projections.
No local performance regression requiring a corrective change was identified.

Measurements represent DTO construction only. They do not claim remote-provider,
message-transport, concurrent-execution, persistent-queue, or SLO performance,
because v4.1.0 intentionally does not implement those capabilities.
