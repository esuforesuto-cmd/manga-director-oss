# v4.3 Vision: Creative Production Platform

## Vision

v4.3 plans a Creative Production Platform that connects the existing
human-governed Autonomous Creative System to end-to-end production planning.
It treats Projects, Assets, Deliverables, publishing preparation, and project
operations as reviewable evidence. It is not an automatic production,
publishing, distribution, or project-control system.

## Desired outcomes

- Make a Project lifecycle visible from approved creative intent to a prepared
  deliverable and human-approved release hand-off.
- Make asset provenance, version, dependency, validation, and distribution
  eligibility inspectable without changing asset storage contracts.
- Make export, target, channel, schedule, and publication history planning
  reviewable without uploading or publishing anything.
- Make team workspace, task board, progress, KPI, and project analytics
  evidence available without allocating work or changing project state.

## Design principles

- Additive: preserve the v4.2 public Python API, CLI, FastAPI, MCP, Web UI,
  Repository, Workflow, Provider, Backend, Plugin, and Extension SDK surface.
- Human governed: all release, distribution, approval, and operational actions
  remain explicit human decisions.
- One Page: every workflow-oriented proposal addresses exactly one existing
  Page and delegates legal transitions to the StateMachine.
- Evidence first: plans may describe, validate, compare, and report; they must
  not dispatch, persist, publish, schedule, allocate, or mutate.
- Portable: proposed DTOs are transport-neutral and presentation-independent.

## Non-goals

v4.3 does not authorize automatic publishing or distribution, autonomous
execution, automatic approval, workflow-stage skipping, multi-page generation,
Provider or Backend additions, Cloud SaaS, marketplace, distributed runtime,
or a Core architecture redesign.

## Migration strategy

| Stage | Additive planning outcome | Required guard |
| --- | --- | --- |
| Inventory | Project, asset, deliverable, target, and KPI vocabulary. | Existing Project and Repository interfaces remain canonical. |
| Planning | Read-only lifecycle, catalog, publishing, and operations reports. | No transition, write, dispatch, upload, or schedule. |
| Validation | Deterministic policy and readiness checks on supplied evidence. | StateMachine, storyboard, quality-review, and human-approval gates remain authoritative. |
| Future adoption | Separately approved opt-in implementation candidates. | Compatibility, security, rollback, ownership, and operational review. |

The development branch remains in the `4.2.x` line until a separately approved
v4.3 implementation and release process changes the version.
