# v3.3.0 Benchmark Verification

v3.3.0 makes no machine-independent latency claim. Provider-free benchmark
smoke covers Production Pipeline, Quality Intelligence, Asset Lifecycle,
Project Intelligence, Production/Quality/Asset/Project Governance, Repository,
Workflow, Diagnostics, Reporting, and Health DTO projection paths.

The smoke checks detect obvious local regressions only. They do not invoke a
Provider, Backend, Agent, remote service, workflow execution, or write path.
No performance regression requiring a workflow-path correction was observed in
the final local validation.
