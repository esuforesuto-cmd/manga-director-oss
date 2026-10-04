# Vision v3.2: Creative Studio and Production Evidence

## Vision Update

v3.2 evolves manga-director from a safe, headless production OS into a more
coherent creative-production platform. The goal is not autonomous creation: it
is to make human decisions, assets, workflow evidence, and production outcomes
easier to understand through additive, transport-neutral designs.

## Creative Studio Vision

Creative Studio is a family of human-owned workspace views for project, story,
page, and review evidence. A future workspace can arrange information, pending
decisions, and hand-offs, but it must not gain workflow execution, approval, or
artifact-mutation authority.

## Asset Intelligence

Asset Intelligence will describe a catalog, metadata, relationships, versions,
search projections, and usage analytics through existing Repository-derived
evidence. It requires provenance, ownership, retention, redaction, and human
review policies before any new persistence is proposed.

## Production Analytics

Project, quality, review, Knowledge, release, and productivity analytics are
bounded observations. They explain evidence and trends; they do not tune a
workflow, alter configuration, operate a deployment, or authorize a release.

## Workflow Evolution

Workflow templates, pipeline profiles, execution profiles, stage validation,
metrics, and pipeline analytics are planning aids. StateMachine remains the
only transition authority, WorkflowEngine remains the execution path, and one
workflow execution still produces exactly one Page.

## Migration Strategy

| Stage | Additive design outcome | Non-negotiable compatibility rule |
| --- | --- | --- |
| 0 — protect v3.1 | Freeze public contracts and capture compatibility fixtures. | No Core, state, persistence, or public API change. |
| 1 — studio evidence | Design workspace layouts and sessions. | No workflow dispatch, artifact write, or approval. |
| 2 — asset evidence | Design catalog, metadata, relationship, and usage projections. | Repository remains canonical; no hidden store or implicit write. |
| 3 — profile evidence | Design template/profile validation and metrics. | StateMachine controls all legal stages and transitions. |
| 4 — analytics evidence | Design bounded reports and dashboards. | No scheduler, collector, deployment, or release automation. |
| 5 — reviewed implementation | Admit small opt-in Issues after rollback and compatibility review. | Preserve all v1.x–v3.1 mandatory workflow guards. |

This vision does not authorize autonomous AI, Cloud SaaS, a marketplace,
distributed runtime, a Core redesign, or a breaking change.
