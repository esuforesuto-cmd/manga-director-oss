# v5.6 Technical Debt Registry

| Area | Current position | Deferred work |
| --- | --- | --- |
| Stability Monitoring | Maintenance signals are validated by explicit local commands. | Telemetry, alerts, scheduling, retained operational history, and incident automation. |
| Regression Baseline | One-page Engine flow and package checks are reproducible locally. | Cross-platform performance history and hosted benchmark storage. |
| Export Engine | Print, Web, eBook, package, metadata, bundle, and archive readiness are diagnosed. | Actual file generation, packaging, publication, and external delivery. |
| Quality Trend | Test, type, lint, package, and benchmark results can be recorded per maintenance review. | Automatic collection, trend persistence, threshold enforcement, and remediation. |
| Release Operations | Documentation and local package evidence are synchronized. | External CVE review, signing, protected CI, GitHub release, and PyPI publication. |

All deferred items require separate approval and must preserve the one-page
StateMachine workflow invariants.
