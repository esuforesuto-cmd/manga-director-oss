# manga-director v3 Development Planning Report

## Outcome

Phase 69 establishes the v3.0 design baseline for evolving
`manga-director` toward a human-directed manga production OS. The work is
planning and documentation only. No Core code, runtime feature, version,
workflow behavior, public API, provider behavior, persistence format, or
execution authority was changed.

## Design delivered

| Area | Planning result |
| --- | --- |
| Vision and migration | [VISION_v3.md](VISION_v3.md) defines the mission, non-goals, long-term shape, and staged migration. |
| Architecture | [ARCHITECTURE_V3.md](ARCHITECTURE_V3.md) assigns Director, Planning, Knowledge, Creative, Agent, Review, Memory, and Presentation responsibilities without a Core dependency inversion. |
| AI Director | [AI_DIRECTOR_PLATFORM.md](AI_DIRECTOR_PLATFORM.md) defines goal, task-graph, strategy, decision-trace, review, and iteration planning DTO boundaries. |
| Multi-agent | [MULTI_AGENT.md](MULTI_AGENT.md) defines role capability and coordination planning without agent-to-agent execution. |
| Knowledge | [KNOWLEDGE_GRAPH.md](KNOWLEDGE_GRAPH.md) defines repository-derived, redacted, governed knowledge projections. |
| Creative pipeline | [CREATIVE_PIPELINE.md](CREATIVE_PIPELINE.md) maps story through review planning to mandatory existing Page gates. |
| Issue and benchmark planning | [ROADMAP_v3.md](ROADMAP_v3.md), [GITHUB_V3_PLAN.md](GITHUB_V3_PLAN.md), and [V3_BENCHMARK_PLAN.md](V3_BENCHMARK_PLAN.md) make work reviewable and measurable. |

## Compatibility decision

v2.7 remains the implementation baseline. All v3 services are proposed as
additive application-layer DTO services over existing public ports. In
particular:

- `StateMachine` stays the only transition authority.
- `WorkflowEngine` stays the only component that invokes an Agent.
- Exactly one Page is produced per execution; workflow stages cannot be
  skipped; a storyboard must persist before generation; quality review must
  complete before human approval; and multi-page generation stays prohibited.
- Existing CLI, FastAPI, MCP, Web UI, Repository, Plugin, Extension SDK, LLM,
  and image-adapter contracts remain compatible.

## Quality gates and implementation admission

The v3 gates in [QUALITY_GATES.md](QUALITY_GATES.md) require Director Planning,
Knowledge, Creative Pipeline, Architecture, and Compatibility validation. A
future Issue must prove that it is non-executing unless separately designed,
approved, and compatible with the established workflow authority model.

## Recommended next action

Accept **V3-ARC-01** and **V3-DIR-01** as design-review Issues first. Their
review should verify that proposed immutable DTOs can derive one legal next
Page step without importing a v3 module into the v2 Core.

## Planning self-review

| Criterion | Assessment | Evidence |
| --- | --- | --- |
| Architecture preservation | 5 / 5 | Dependency direction and execution authority are explicit. |
| Backward compatibility | 5 / 5 | No source/API/version change; compatibility gate is mandatory. |
| Safety | 5 / 5 | All planned surfaces are advisory and retain one-Page guards. |
| Extensibility | 4 / 5 | Layer and Issue boundaries are clear; concrete ports await reviewed needs. |
| Documentation readiness | 5 / 5 | Vision, architecture, roadmaps, examples, benchmarks, and report are linked. |

Remaining design questions (not implementation authorization): retention and
ownership policy for derived knowledge, measurable workload fixtures for
knowledge planning, and a future conflict-policy review for multi-agent
recommendations.
