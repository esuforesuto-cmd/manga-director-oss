# v3.4 Architecture Planning

## Status

This document plans additive v3.4 work on the `3.3.x` development branch. It
does not change Core Architecture, public APIs, workflow execution, repository
serialization, or adapter contracts.

## Planned Responsibilities

| Platform | Planned responsibility | Must not do |
| --- | --- | --- |
| Knowledge Platform | Catalog, relationships, search strategy, quality, governance, and insights. | Write, merge, repair, fetch remotely, or replace Repository. |
| Production Operations | Dashboard, monitoring evidence, capacity, incident timeline, audit, and analytics. | Deploy, configure, remediate, schedule, or alert. |
| Organization Intelligence | Redacted team/role/workload/collaboration/risk/confidence projections. | Score people, assign work, alter membership, or commit delivery. |
| Release Intelligence | Dashboard, metrics, deployment/compatibility/regression analytics, and release health. | Tag, sign, publish, deploy, approve, or release. |
| Analytics Platform | Bounded aggregation and explainable reports. | Collect externally or perform an operational action. |
| Operations Platform | Readiness and maintenance interpretation. | Execute remediation, deployment, or configuration changes. |
| Developer Platform | Fixtures, examples, benchmarks, migration, and compatibility tooling. | Widen root APIs or bypass quality gates. |

## Dependency Direction

```text
CLI / FastAPI / MCP / Web UI
        -> optional v3.4 Application DTO services
        -> existing v3.3 Application services and public ports
        -> Core Domain / StateMachine / WorkflowEngine / Repository contracts
```

No Core module imports a v3.4 module. Presentation adapters render shared DTOs.
The Repository interface remains canonical. WorkflowEngine remains the only
Agent-execution path.

## Admission Constraints

Every v3.4 Issue must prove exactly one Page per execution. StateMachine-derived
legal transitions remain mandatory; no stage can be skipped. A storyboard must
persist before generation and quality must complete before approval. No Issue
may permit multi-page generation, implicit writes, Provider or Agent calls,
personnel action, scheduling, deployment, tagging, signing, publication, or
release action.
