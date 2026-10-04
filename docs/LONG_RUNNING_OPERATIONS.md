# Long-Running Operations

`LongRunningDiagnostics` retains a bounded history of passive task lifecycle
summaries from `MetricsRegistry`. Each capture reports workflow and batch
counters, optional tracemalloc memory evidence, and an operator-supplied
graceful-recovery summary.

The component never enables tracemalloc itself. When a host has enabled it,
memory current/peak/growth are reported; otherwise it records a safe zero-value
snapshot marked `tracing_enabled: false`. This avoids changing the host's memory
profiling behavior.

The data is in-process diagnostic evidence, not a persistent telemetry system,
leak detector, scheduler, or alerting service. Use the bounded report alongside
existing Repository and Recovery validation during long-lived operation.
