# manga-director v3.2 Development Planning Report

## Outcome

Phase 81 establishes the v3.2 planning baseline on the v3.1.x development
branch. It adds design documents, Issue taxonomy, examples, benchmark plans,
quality gates, and Technical Debt direction only. No Core code, runtime feature,
version, workflow behavior, public API, provider, persistence format, or
execution authority changed.

## Design Delivered

| Area | Planning result |
| --- | --- |
| Vision and migration | [VISION_v3_2.md](VISION_v3_2.md) and [UPGRADE_GUIDE_v3_2.md](UPGRADE_GUIDE_v3_2.md) define staged additive evolution. |
| Architecture | [ARCHITECTURE_V3_2.md](ARCHITECTURE_V3_2.md) preserves Core and dependency direction. |
| Creative Studio | [CREATIVE_STUDIO.md](CREATIVE_STUDIO.md) defines workspace and review candidates. |
| Asset Intelligence | [ASSET_INTELLIGENCE.md](ASSET_INTELLIGENCE.md) defines catalog, metadata, search, lifecycle, and analytics candidates. |
| Workflow and analytics | [ROADMAP_v3_2.md](ROADMAP_v3_2.md) defines profile, validation, metric, and analytics work. |
| Issues and quality | [GITHUB_V3_2_PLAN.md](GITHUB_V3_2_PLAN.md), [V3_2_BENCHMARK_PLAN.md](V3_2_BENCHMARK_PLAN.md), and [V3_2_QUALITY_GATES.md](V3_2_QUALITY_GATES.md) make work reviewable. |

## Compatibility Decision

v3.1 remains the implementation baseline. Future services are additive,
transport-neutral, non-executing DTO consumers of existing ports. StateMachine
remains transition authority. WorkflowEngine remains the only Agent-execution
path. Exactly one Page is produced per execution. Stages are never skipped.
A storyboard persists before generation. Quality completes before approval.
Multi-page generation remains prohibited.

## Recommended First Issues

Review V32-ARC-01, V32-STU-01, V32-AST-01, V32-WFL-01, and V32-ANL-01.
These are design-only Issues. Each needs compatibility and non-execution proof
before an implementation proposal is admitted.

## Planning Self-Review

| Criterion | Assessment |
| --- | ---: |
| Architecture preservation | 5/5 |
| Backward compatibility | 5/5 |
| Safety | 5/5 |
| Extensibility | 5/5 |
| Documentation readiness | 5/5 |
