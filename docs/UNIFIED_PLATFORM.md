# Unified Creative Platform

## Purpose

The Unified Creative Platform is a v4.8 design boundary for composing existing
creative-production information. It is not a replacement application, a new
database, or a control plane. It standardizes how modules describe scope,
evidence, review readiness, and lifecycle references.

## Conceptual platform packet

| Part | Content | Source modules |
| --- | --- | --- |
| Scope | Project, one optional Page, participant, and correlation references. | Workspace, Production, Decision Platform |
| Evidence | Caller-supplied findings, summaries, provenance, redaction, and freshness. | Knowledge, Quality, Governance, Analytics |
| Plan | Advisory alternatives, dependencies, prerequisites, and human owner. | Agent Platform, Decision Platform, Production |
| Review | Review coverage, quality status, approval readiness, and escalation references. | Review, Quality, Enterprise, Decision Platform |
| Lifecycle | Snapshot, timeline, retention, and source references. | Workspace, Knowledge, Production, Release |
| Operations | Read-only health, trend, risk, capacity, and reliability summaries. | Enterprise, Production, Analytics |

## Canonical boundaries

- A platform packet may describe a Page, but it cannot create or mutate one.
- A workflow packet is always one-Page scoped and cannot contain a batch of
  generation requests.
- It cannot generate an image without persisted storyboard evidence, approve a
  Page without completed quality review evidence, or skip a workflow stage.
- It cannot persist an aggregate, invoke an Agent, call a Provider, grant a
  permission, or make an external request.
- Presentation clients may render platform packets but do not become their
  owner; DTOs remain transport-neutral.

## Future additive facade

The proposed facade is intentionally unnamed in code until a separate issue
establishes its public contract. It will accept existing service instances and
supplied DTOs, return an immutable aggregate DTO, preserve existing module
entry points, and expose source links rather than duplicate domain records.

## Consolidation decision rule

A concern may be shared only when it has identical semantics across modules,
has an explicit source/provenance model, and can be expressed without a write
or authority transfer. Otherwise the owning module remains the only source of
truth and the platform merely links to it.
