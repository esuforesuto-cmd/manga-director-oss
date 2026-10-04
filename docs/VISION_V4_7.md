# v4.7 Vision: Creative Decision Platform

## Vision

v4.7 defines a local-first Creative Decision Platform above stable v4.6.0. It
connects AI-generated analysis, accountable human review, and organization
governance evidence without turning any system into an autonomous decision or
execution runtime.

## Desired outcomes

- Define a Decision Engine that makes goals, evidence, alternatives, trade-offs,
  risk, confidence, and human ownership explicit.
- Define Review Intelligence that summarizes supplied creative, quality,
  workflow, operational, and governance findings for a reviewer.
- Define a Recommendation Framework that explains advisory options without
  selecting, accepting, or applying one.
- Define an Approval Platform that models manual approval points, escalation,
  override rationale, and decision history without granting or enforcing access.
- Define an Executive Dashboard that composes redacted decision health and
  organizational evidence into a transport-neutral view model.

## Design principles

- **Additive:** Preserve v4.6 public Python API, CLI, FastAPI, REST, MCP, Web
  UI, Repository, Workflow, Agent, Plugin, Extension SDK, Provider, and Backend
  contracts.
- **Human accountable:** AI contributes explainable evidence only; a named human
  retains decision, approval, escalation, and override responsibility.
- **Evidence first:** Inputs are caller-supplied, local, attributable, scoped,
  and redacted as needed; outputs are immutable DTOs and reports.
- **Core authority:** StateMachine, WorkflowEngine, Project, and existing
  Repository interfaces remain canonical.
- **One Page:** Workflow-related decisions are scoped to exactly one existing
  Page and retain storyboard, completed-quality-review, and human-approval
  gates.
- **Organization-safe:** No implicit access, cross-team data transfer, policy
  enforcement, monitoring, Cloud service, or external action is introduced.

## Non-goals

v4.7 does not authorize autonomous decisions or execution, automatic approval,
policy enforcement, agent dispatch, workflow mutation, stage skipping,
multi-page generation, hidden evidence collection, shared decision persistence,
organization/tenant routing, Cloud SaaS, payment, billing, marketplace
operation, distributed runtime, or a Core Architecture redesign.
