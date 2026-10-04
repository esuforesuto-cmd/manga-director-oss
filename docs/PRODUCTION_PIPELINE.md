# Production Pipeline Planning

Production Pipeline is a planning surface for human-owned production flow. It
may describe templates, visible stages, approval and publishing prerequisites,
validation evidence, and metrics, but it must not execute or alter a workflow.

| Candidate | Design boundary | Required evidence before implementation |
| --- | --- | --- |
| Pipeline Templates | Describe reusable legal-stage configurations. | StateMachine mapping, versioning, and no-application proof. |
| Production Stages | Project existing StateMachine stage evidence. | One-Page scope and no-transition proof. |
| Approval Pipeline | Display required human decision checkpoints. | Completed-quality-review and no-auto-approval proof. |
| Publishing Pipeline | Describe publication prerequisites and hand-off evidence. | No upload, tag, release, or publish action. |
| Pipeline Validation | Compare supplied evidence with declared policy. | Deterministic fixture and no-remediation proof. |
| Pipeline Metrics | Aggregate bounded stage evidence. | Redaction, observation window, and no-scheduler proof. |

## v4.3 Creative Production Platform design

v4.3 extends this planning vocabulary without changing the existing pipeline
surface. The proposed Production Pipeline adds Project Lifecycle, Production
Workflow, Milestone Management, Deliverable Management, and Release Workflow
reports. All are read-only, human-owned DTO proposals.

| Proposed record | Purpose | Explicitly not allowed |
| --- | --- | --- |
| Lifecycle Plan | Show current evidence and a possible next legal stage. | Transitioning a Page or skipping a stage. |
| Production Workflow Plan | Describe the one-Page evidence required for a stage. | Dispatching, generating, or changing workflow data. |
| Milestone Plan | Compare supplied milestones and readiness criteria. | Completing a milestone or scheduling work. |
| Deliverable Plan | Identify a human-reviewable prepared output. | Creating, exporting, uploading, or distributing output. |
| Release Workflow Plan | Present release prerequisites and a hand-off checklist. | Approving, tagging, publishing, or notifying. |

Any future workflow-related plan must continue to address exactly one existing
Page, require a persisted storyboard before image generation, require completed
quality review before approval, and delegate transition validation to the
StateMachine.

## v5.6 Manga Production Pipeline v1

Production Pipeline v1 standardizes a read-only human workflow for one existing
Page: **Story → Character → Page → Art → Review → Export**. It is an advisory
projection of the existing `WorkflowContext`; it does not dispatch work, create
an image, approve a Page, create an export, or modify the StateMachine.

The service reuses supplied `story_context`, `character_context`,
`world_context`, and `timeline_context` evidence in a compact prompt brief.
This prevents repeated context in delivery prompts while retaining the required
one-page, storyboard, quality-review, and human-approval constraints.

| Pipeline | Required evidence | Advisory outcome |
| --- | --- | --- |
| Story | Story and timeline context | Continuity readiness or missing evidence. |
| Character | Character and world context | Consistency readiness or missing evidence. |
| Page | Exactly one Page and current state | Next legal StateMachine command. |
| Art | `Storyboarded` workflow artifact | Whether `generate` is the next legal command. |
| Review | `QualityChecked` workflow artifact | Whether a human may consider approval. |
| Export | Approved Page plus completed quality review | Export eligibility only; no export is performed. |

`V56ProductionPipelineService.production_pipeline()` returns immutable DTOs and
never changes a context. Delivery adapters retain their existing interfaces and
must execute any legal transition through the domain StateMachine.
