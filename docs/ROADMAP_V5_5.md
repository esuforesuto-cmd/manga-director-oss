# v5.5 Lifecycle Roadmap

v5.5 begins from the v5.4.0 Final baseline on the `5.4.x` development branch. This roadmap is design-only and does not authorize implementation or a version change.

## Must

| Issue | Deliverable | Acceptance criteria |
| --- | --- | --- |
| V5.5-01 | Lifecycle Framework | Support phases, owner, evidence, unknown state, and review date are explicit DTO fields. |
| V5.5-02 | Upgrade Framework | Source/target compatibility manifest, preconditions, risk, and rollback evidence remain human-gated. |
| V5.5-03 | Deprecation Policy | Notice, replacement, horizon, exception, and v5.0 LTS safeguards are reviewable. |
| V5.5-04 | Platform Health | Health dimensions expose evidence freshness and unknown status without monitoring or repair. |
| V5.5-05 | Maintenance Strategy | Maintenance reports consolidate compatibility, support, release, and operational evidence without ownership changes. |

## Should

- Define fixture matrices for active, maintained, deprecated, blocked, and unknown evidence.
- Draft presentation-neutral JSON and Markdown report contracts.
- Define documentation ownership and review cadence for public compatibility commitments.

## Could

- Provide example maintenance plans for an SDK capability and an extension capability.
- Explore offline historical health summaries after evidence provenance and retention are separately approved.

## Won't

- Automatic upgrades, package execution, configuration changes, deprecation enforcement, telemetry collection, alerting, repair, workflow mutation, or publication.
- Core Architecture redesign, new providers/backends, Cloud SaaS, or distributed runtime.
