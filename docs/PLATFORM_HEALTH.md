# Platform Health Design

## Purpose

Platform Health is a read-only, evidence-oriented summary of supplied platform signals. It makes maintenance posture visible without collecting telemetry, dispatching alerts, or repairing a runtime.

## Planned health dimensions

| Dimension | Evidence examples | Boundary |
| --- | --- | --- |
| Compatibility | Contract, regression, and extension checks. | Does not run tests or change callers. |
| Maintenance | Support phase, owner, review date, and open debt. | Does not create work or assign people. |
| Release readiness | Package, documentation, security, and quality evidence. | Does not sign, tag, upload, or publish. |
| Operational posture | Supplied configuration and diagnostics status. | Does not probe, monitor, alert, or recover. |
| Evidence freshness | Timestamp and provenance classification. | Does not retain history or fabricate missing data. |

## Status model

Each dimension is healthy, attention-required, blocked, or unknown. Unknown is a first-class state and must not be rendered as healthy. The aggregate is advisory and requires a human owner to interpret.

## Safety boundary

Platform Health cannot affect Pages, workflow stages, image generation, review approval, policy enforcement, repository data, or runtime execution.
