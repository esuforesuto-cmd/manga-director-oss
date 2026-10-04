# v3.3 Architecture Planning

## Status

This document plans additive v3.3 work only. It does not change Core
Architecture, public APIs, workflow execution, repository serialization, or
adapter contracts.

## Planned Responsibilities

| Platform | Planned responsibility | Must not do |
| --- | --- | --- |
| Production Pipeline | Templates, stage views, approval/publishing prerequisites, validation, and metrics. | Execute, transition, publish, or approve. |
| Quality Platform | Quality dashboards, review/consistency metrics, regressions, and trends. | Complete review, decide quality, or authorize approval. |
| Asset Lifecycle | History, archive policy, dependency graphs, audits, and lifecycle analytics. | Replace Repository, archive/delete implicitly, or fetch remotely. |
| Project Intelligence | Health, schedule, resource, milestone, risk, and forecast projections. | Schedule, allocate, commit delivery, or mutate a Project. |
| Analytics Platform | Bounded aggregation and explainable reporting. | Collect externally or make an operational action. |
| Operations Platform | Readiness and maintenance interpretation. | Deploy, configure, publish, or remediate. |
| Developer Platform | Fixtures, examples, benchmark plans, compatibility tooling. | Widen root APIs or bypass quality gates. |

## Dependency Direction

```text
CLI / FastAPI / MCP / Web UI
        -> optional v3.3 Application DTO services
        -> existing v3.2 Application services and public ports
        -> Core Domain / StateMachine / WorkflowEngine / Repository contracts
```

No Core module imports a v3.3 module. Presentation adapters render shared DTOs.
The Repository interface remains canonical. WorkflowEngine remains the only
Agent-execution path.

## Admission Constraints

Every v3.3 Issue must prove exactly one Page per execution. It must use
StateMachine-derived legal transitions and never skip a stage. A storyboard
persists before generation and quality completes before approval. No Issue may
allow multi-page generation, implicit writes, Provider or Agent calls,
scheduling, archive/delete actions, publishing, or release actions.
