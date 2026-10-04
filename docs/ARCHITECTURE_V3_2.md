# v3.2 Architecture Planning

## Status

This document plans additive v3.2 work only. It does not change Core
Architecture, public APIs, workflow execution, repository serialization, or
adapter contracts.

## Planned Responsibilities

| Platform | Planned responsibility | Must not do |
| --- | --- | --- |
| Creative Studio | Workspace layouts, sessions, dashboards, story/page/review views. | Execute, transition, write, or approve. |
| Asset Platform | Catalog, metadata, relationships, search, versions, usage. | Replace Repository, fetch remotely, or persist implicitly. |
| Knowledge Platform | Asset and creative provenance/relationship policy. | Merge, repair, or mutate knowledge. |
| Workflow Intelligence | Templates, profiles, stage validation, metrics, pipeline analysis. | Schedule, optimize, or alter a workflow. |
| Analytics Platform | Project, quality, review, Knowledge, release, productivity reports. | Collect externally or take an operational action. |
| Operations Platform | Readiness and maintenance interpretation. | Deploy, configure, publish, or remediate. |
| Developer Platform | Fixtures, examples, benchmark plans, compatibility tooling. | Widen the root API or bypass gates. |

## Dependency Direction

```text
CLI / FastAPI / MCP / Web UI
        -> optional v3.2 Application DTO services
        -> existing v3.1 Application services and public ports
        -> Core Domain / StateMachine / WorkflowEngine / Repository contracts
```

No Core module imports a v3.2 module. Presentation adapters render shared DTOs.
The Repository interface remains canonical. WorkflowEngine remains the only
Agent-execution path.

## Admission Constraints

Every v3.2 Issue must prove one explicitly scoped Page per execution.
It must use StateMachine-derived legal transitions and never skip a stage.
A storyboard persists before generation and quality completes before approval.
No Issue may allow multi-page generation, implicit writes, Provider or Agent
calls, scheduling, or release actions.
