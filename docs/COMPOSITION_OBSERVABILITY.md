# Composition Observability

`CompositionObservabilityService` turns a composition preview into five local
observations: registry, Feature Packs, Platform Profile, Solution Templates,
and Composition Engine. The status reflects only supplied composition metadata.

No telemetry, probes, alerts, monitoring process, dashboard publication, or
report persistence is started. This keeps observability compatible with the
local-first v5.0 LTS model and prevents unsupported runtime-health claims.
