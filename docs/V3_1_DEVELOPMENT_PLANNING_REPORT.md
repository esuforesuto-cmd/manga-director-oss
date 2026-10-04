# manga-director v3.1 Development Planning Report

## Outcome

Phase 75 establishes the v3.1 development-planning baseline on the v3.0.x
branch. It is documentation, Issue, example, and benchmark planning only. No
Core code, runtime feature, version, workflow behavior, public API, provider,
persistence format, or execution authority changed.

## Design delivered

| Area | Planning result |
| --- | --- |
| Vision and migration | [VISION_v3_1.md](VISION_v3_1.md) defines production goals, collaboration, Knowledge evolution, operations, and staged migration. |
| Architecture | [ARCHITECTURE_V3_1.md](ARCHITECTURE_V3_1.md) assigns additive v3.1 responsibilities without Core dependency inversion. |
| Director | [ROADMAP_v3_1.md](ROADMAP_v3_1.md) defines long-term objectives, templates, history, strategy, and metrics candidates. |
| Collaboration | [CREATIVE_COLLABORATION.md](CREATIVE_COLLABORATION.md) defines human workspace and hand-off candidates. |
| Knowledge | [KNOWLEDGE_EVOLUTION.md](KNOWLEDGE_EVOLUTION.md) defines version, diff, merge-plan, snapshot, timeline, and analytics policy candidates. |
| Operations | [OPERATIONS_PLATFORM.md](OPERATIONS_PLATFORM.md) defines report-only observability and analytics candidates. |
| Issues and benchmarks | [GITHUB_V3_1_PLAN.md](GITHUB_V3_1_PLAN.md) and [V3_1_BENCHMARK_PLAN.md](V3_1_BENCHMARK_PLAN.md) make work reviewable and measurable. |

## Compatibility decision

v3.0 remains the implementation baseline. Future services are additive,
transport-neutral, non-executing DTO consumers of existing ports. `StateMachine`
remains transition authority; `WorkflowEngine` remains the only Agent-execution
path. Exactly one Page is produced per execution; no stage is skipped; a
storyboard persists before generation; quality completes before approval; and
multi-page generation remains prohibited.

## Recommended first Issues

Review V31-ARC-01, V31-DIR-01, V31-COL-01, V31-KNOW-01, and V31-OPS-01 as
design-only Issues. Each must include a compatibility fixture and an explicit
non-execution proof before an implementation proposal is admitted.

## Planning self-review

| Criterion | Assessment | Evidence |
| --- | --- | --- |
| Architecture preservation | 5/5 | Dependency direction and Core authority remain explicit. |
| Backward compatibility | 5/5 | Version and public contracts remain unchanged. |
| Safety | 5/5 | Collaboration, Knowledge, and operations are advisory and non-mutating. |
| Extensibility | 5/5 | Issue ownership, dependencies, migration, examples, and benchmarks are defined. |
| Documentation readiness | 5/5 | Vision, architecture, roadmap, Issue plan, quality gates, debt, examples, and benchmark plan are linked. |
