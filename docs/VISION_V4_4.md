# v4.4 Vision: Enterprise Creative Platform

## Vision

v4.4 designs an Enterprise Creative Platform above the stable v4.3 Creative
Production Platform. It makes enterprise workspace boundaries, team
collaboration, portfolio visibility, extension discovery, and workflow
marketplace governance reviewable without turning manga-director into a hosted
service, changing Core authority, or executing a marketplace workflow.

## Desired outcomes

- Define a unified, human-owned Enterprise Workspace vocabulary that can
  aggregate existing Project evidence without mutating a Project or its state.
- Define collaboration, role, review, handoff, and approval boundaries that
  complement the StateMachine rather than replace it.
- Define Portfolio reporting for project health, milestone, capacity, risk, and
  delivery evidence without allocating work or controlling schedules.
- Define a Workflow Marketplace catalog, compatibility, provenance, and review
  model without installing, downloading, executing, billing, or publishing
  marketplace content.
- Define an Extension Ecosystem contract for discovery, capability description,
  compatibility, isolation, lifecycle, and governance without changing the
  existing Extension SDK or loading extensions automatically.

## Design principles

- **Additive:** Preserve v4.3 public Python API, CLI, FastAPI, REST, MCP, Web
  UI, Repository, Workflow, Provider, Backend, Plugin, and Extension SDK
  contracts.
- **Core authority:** The StateMachine, WorkflowEngine, and existing Repository
  ports remain canonical.
- **Human governed:** Workspace access, collaboration, portfolio decisions,
  extension approval, and marketplace admission are explicit human decisions.
- **Evidence first:** The planned surfaces describe, compare, validate, and
  report supplied evidence; they do not write, dispatch, install, execute,
  publish, allocate, or bill.
- **One Page:** Workflow-related planning is scoped to one existing Page and
  retains persisted-storyboard and completed-quality-review requirements.
- **Local by default:** v4.4 is not Cloud SaaS, a multi-tenant service, or a
  distributed runtime.

## Non-goals

v4.4 does not authorize autonomous AI, automatic approvals, multi-page
generation, workflow-stage skipping, workspace or portfolio mutation,
role/permission enforcement, task dispatch, schedule automation, marketplace
download/install/publish, extension execution, payment, billing, Cloud SaaS,
or a Core architecture redesign.

## Migration strategy

| Stage | Additive planning outcome | Compatibility guard |
| --- | --- | --- |
| Vocabulary | Workspace, team, portfolio, marketplace, and extension DTO terminology. | Existing Project, Repository, Plugin, and Extension SDK contracts remain canonical. |
| Read-only projection | Human-reviewed workspace, collaboration, portfolio, catalog, and compatibility reports. | No write, transition, allocation, install, load, execute, publish, or network action. |
| Governance design | Explicit policy, provenance, approval, redaction, isolation, and rollback requirements. | StateMachine, storyboard, quality-review, and human-approval gates remain authoritative. |
| Future opt-in delivery | Separately approved implementation candidates. | Compatibility, security, ownership, rollback, and operational reviews are required per capability. |

The development branch remains `4.3.x`; this planning cycle does not change the
package version.
