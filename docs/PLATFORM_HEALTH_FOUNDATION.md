# Platform Health Foundation

`PlatformHealthFoundation` aggregates caller-supplied compatibility, maintenance, release, operations, and evidence-freshness signals. The status model preserves `unknown` rather than treating missing evidence as healthy.

This is a read-only diagnostic component. It does not collect telemetry, probe services, emit alerts, retry work, repair runtime state, or affect any Page or workflow transition.
