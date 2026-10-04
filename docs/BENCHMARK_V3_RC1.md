# v3.0.0 RC1 Benchmark Verification

Provider-free benchmark smoke exercises planning, Knowledge, Director, Review,
Repository, Workflow, diagnostics, reporting, and health paths using local mock
metadata and frozen DTO composition. It makes no network request, calls no
Provider, and executes no workflow.

The v2.7 stable baseline does not contain cross-host absolute timing for v3
advisory paths. RC1 therefore uses deterministic local smoke and repeatability
evidence rather than treating a different host as a numeric SLO baseline. No
local regression may be inferred from this document; results are not a
production SLO or cross-machine comparison.

Live providers, cloud monitoring, distributed execution, and autonomous
workflow execution remain excluded from RC benchmark scope.
