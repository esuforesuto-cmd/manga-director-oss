# Performance Analysis

`ProductionInsights.performance_report()` analyzes in-process duration
summaries. It accepts an approved local `PerformanceBaseline` and optional
historical samples, then returns:

- current performance snapshot;
- per-metric baseline comparison;
- supplied performance trend direction;
- regression summary; and
- diagnostic-only optimization recommendations.

No optimizer runs, threshold changes, cache writes, scheduler action, or
workflow change is made. Measurements are provider-free local regression
signals, not a hardware-independent service-level objective.

Use the v2.5 benchmark scripts to record environment, command, iteration count,
and baseline evidence before accepting an optimization Issue.
