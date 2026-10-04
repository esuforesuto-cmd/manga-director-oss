# v5.6 Regression Baseline

The stable v5.6 baseline is the approved single-page flow:

Story → Character → Page → Review → Export

It requires a persisted storyboard before generation and a completed quality
review plus explicit human approval before export readiness. The baseline checks
that all Engine reports leave the supplied `WorkflowContext` unchanged and do
not create files, publish content, or advance the workflow.

The local throughput reference is maintained by
`benchmarks/manga_production_os_v5_6.py`. Results are compared only against
future runs from the same environment and are not a hosted performance claim.

## 2026-08-09 reference run

After one warm-up run (`0.115912s`), three 1,000-projection runs measured
`0.092626s`, `0.088796s`, and `0.094896s`. The maintenance baseline is the
median: **`0.092626s`**.
