# v3.5.0 RC1 Benchmark Verification

v3.5.0 RC1 makes no machine-independent latency claim. Provider-free benchmark
smoke covers Unified Knowledge Graph, Creative Analytics, Production Metrics,
Platform Dashboard, Governance Dashboard, policy validation, compliance report,
audit generation, Repository, reporting, diagnostics, and existing workflow
projection paths.

The smoke checks detect obvious local regressions only. They do not invoke a
Provider, Backend, Agent, remote service, workflow execution, or write path.
No performance regression requiring a workflow-path correction was observed in
the local RC run.
