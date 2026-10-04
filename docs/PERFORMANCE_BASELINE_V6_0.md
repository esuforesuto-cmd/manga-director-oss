# v6.0 Performance Baseline

The provider-free Platform Kernel benchmark is the v6.0 local baseline. It
projects one completed-quality Page context repeatedly without I/O, provider
calls, workflow mutation, persistence, Extension loading, or Marketplace
contact. Final validation completed 500 projections in `0.111484s`.

The shared benchmark smoke harness now includes one `platform_kernel`
projection by reusing this scenario. It reports a local timing only; it does
not introduce a fixed pass/fail threshold or a cross-version comparison.

`benchmarks/baselines/v6_0_platform_kernel.json` records the verified
workload contract: the existing default of 500 iterations, local-only
single-page projection, and read-only, non-executing, non-persistent,
provider-free boundaries. It is structured metadata, not a performance
guarantee or a new benchmark execution path.

No common historical v5.7-to-v6.0 benchmark format is retained, so this is a
baseline rather than a cross-version performance-regression claim.
