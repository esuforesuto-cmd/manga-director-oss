# v3.4.0 RC1 Benchmark Verification

v3.4.0 RC1 makes no machine-independent latency claim. Provider-free benchmark
smoke covers Knowledge Platform, Production Operations, Organization
Intelligence, Release Intelligence, Knowledge/Production/Organization/Release
Governance, Repository, Workflow, Diagnostics, Reporting, and Health DTO
projection paths.

The smoke checks detect obvious local regressions only. They do not invoke a
Provider, Backend, Agent, remote service, workflow execution, or write path.
No performance regression requiring a workflow-path correction was observed in
the local RC run.
