# v4.1 RC1 Benchmark Audit

The RC performance smoke executes local DTO-construction benchmarks for Agent
Runtime, Orchestration, Collaboration Workflow, Event/Observability processing,
and Repository-adjacent read-only projections. These measurements are
provider-free and credential-free.

No local regression requiring a code correction was identified. The benchmarks
measure projection overhead only; they do not claim an SLO for providers, remote
communication, task execution, or persistent queues because none is implemented.
