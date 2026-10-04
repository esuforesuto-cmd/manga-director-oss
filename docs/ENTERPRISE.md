# Enterprise Readiness Backlog

This is a backlog, not an Enterprise feature implementation. It preserves
Core isolation and prohibits secrets in `config.yaml`.

| Area | Candidate Issue | Priority | Outcome and boundary |
| --- | --- | --- | --- |
| Configuration | ENT-01 configuration profiles | P0 | Document local/team/production-like profiles, environment secret references, validation, and reload policy. |
| Repository | ENT-02 repository operating guide | P0 | Define large-project load/save, integrity, backup, recovery, and rollback evidence through Repository ports. |
| Automation | ENT-03 automation scope decision | P1 | Record requirements only; Automation is not a shipped runtime. |
| Notification | ENT-04 delivery operations | P1 | Specify retry, redaction, audit, and failure evidence for existing notification boundaries. |
| Security | ENT-05 security posture review | P0 | Reassess allowed providers, paths, hosts, rate limits, and secret-handling defaults. |
| Audit | ENT-06 audit retention design | P1 | Define event retention, redaction, export, and operator access requirements. |
| Diagnostics | ENT-07 operations report profile | P0 | Define safe health, diagnostics, and incident-report expectations using existing DTOs. |
| Database | ENT-08 PostgreSQL workload evidence | P1 | Measure query, transaction, recovery, and connection behavior without port changes. |
| Plugin | ENT-09 plugin governance | P1 | Define approval, manifest, compatibility, and failure-isolation expectations. |
| Extension SDK | ENT-10 extension compatibility matrix | P1 | Publish SDK/core version fixtures and packaging evidence. |

Every Enterprise Issue must include a threat model, supported-version impact,
mock or fixture strategy, observability evidence, documentation change, and
rollback condition. No row authorizes Cloud SaaS, SSO, distributed workflow,
or a Core redesign.
