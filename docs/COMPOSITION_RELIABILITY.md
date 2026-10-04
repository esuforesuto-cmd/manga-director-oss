# Composition Reliability

`CompositionReliabilityService` reports metadata confidence as
`metadata_valid` or `metadata_invalid`; it deliberately does not represent
runtime health. It is derived from local Composition Observability evidence.

Health checks, fault detection, retries, recovery, runtime reconfiguration,
and automatic recovery are not performed. Invalid composition metadata remains
visible for human correction and is never repaired automatically.
