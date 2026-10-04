# v6 Development Roadmap

## Planning baseline

v6.0 planning starts from stable v5.7.0. No installed-version or public API
change occurs during planning.

## Iteration 1 — Platform Foundation

| Issue | Outcome | Compatibility gate |
| --- | --- | --- |
| V6-01 | Platform, service, and workspace DTO foundations. | v5.x public surfaces unchanged. |
| V6-02 | Collaboration context and human-review reference model. | Existing review ownership unchanged. |
| V6-03 | Knowledge graph references and provenance model. | Repository interfaces unchanged. |
| V6-04 | Automation plan and policy contracts. | StateMachine and WorkflowEngine remain authoritative. |
| V6-05 | Extension capability/compatibility reports. | Existing Plugin API unchanged. |

## Iteration 2 — Intelligence and scale

- Multi-project and multi-workspace summaries with pagination and bounded
  traversal.
- Collaboration, knowledge, and automation diagnostics.
- Portfolio/enterprise observability and scalability benchmarks.
- Opt-in transport adapters for stable query/report APIs only.

## Iteration 3 — Governance and release readiness

- Policy, audit, retention, and reliability reports.
- Extension trust and marketplace design validation.
- Compatibility matrix, migration rehearsal, security review, and release
  performance baseline.

## Quality gates

Architecture, platform-boundary, backward-compatibility, and scalability
reviews are required for every iteration. No implementation may weaken the
one-page StateMachine invariants.
