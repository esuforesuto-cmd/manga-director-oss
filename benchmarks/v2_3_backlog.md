# v2.3 Benchmark Backlog

These scenarios are specifications only until an approved Issue introduces a
mock contract and deterministic harness. They do not make network calls.

| Scenario | Purpose | Baseline and CI rule |
| --- | --- | --- |
| `provider_latency` | Measure mock request normalization and provider Factory overhead | provider-neutral fixture; no live latency in CI |
| `image_backend_latency` | Measure mock generator dispatch and result normalization | mock image backend; no image generation in CI |
| `repository_large_scale` | Measure selective read/save and history queries for large Projects | provider-free fixture and retained threshold |
| `workflow_large_scale` | Measure repeated legal one-page transitions at scale | StateMachine-safe fixture and retained threshold |

Record Python version, OS, CPU, storage/database profile, run count, median,
p95, and rollback threshold in every future benchmark Issue.
