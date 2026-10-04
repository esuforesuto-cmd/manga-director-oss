# v2.4.0 RC1 Benchmark Verification

## Method

The RC gate runs deterministic, provider-free benchmark smoke scenarios and
the retained repeatability/regression tests. Results are local regression
evidence, not hardware-independent service-level objectives.

## Covered boundaries

- Workflow, resume validation, recovery simulation, and long-running runtime;
- Repository, database, integrity, and Batch resume;
- configuration, Provider/Image Backend discovery, inventory, health, and lifecycle;
- diagnostics, production runtime, operations, notification, automation,
  Plugin, Extension, and event dispatch.

No scenario sends a provider request, generates an image, invokes a cloud
service, or executes distributed work. Any performance regression must be
corrected only when reproducible against retained provider-free evidence.
