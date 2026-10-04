# v5.0 Vision: One Creative Platform

## Vision

v5.0 defines **One Creative Platform**: a coherent, local-first composition
model for the capabilities introduced from v2 through v4. It favors a small
set of understandable contracts over new feature areas, while preserving every
supported v4.8 public surface.

## Mission

Make Workspace, Knowledge, Agents, Production, Enterprise, Decision, and
Ecosystem capabilities easier to discover, compose, and govern without moving
their source of truth or changing their behavior.

## Design principles

1. **Compatibility before consolidation.** Existing Python, CLI, FastAPI/REST,
   MCP, Web UI, Repository, Workflow, Plugin, Extension SDK, Provider, and
   Backend contracts stay supported.
2. **Compose; do not replace.** A unified surface delegates to existing public
   services and never recreates Core behavior.
3. **One authority for workflow state.** The StateMachine remains the only
   transition authority; a workflow execution produces exactly one Page.
4. **Explicit evidence.** Context, reports, recommendations, and dashboards
   carry source, freshness, owner, and review requirements.
5. **Human-governed operation.** No automatic approval, autonomous execution,
   service routing, policy enforcement, or external action is authorized.
6. **Incremental adoption.** Unified APIs and SDKs are optional adapters;
   legacy interfaces remain valid throughout v5.0.

## Non-goals

- Core, StateMachine, WorkflowEngine, or Repository redesign.
- API removal, forced migration, or a shared persistence conversion.
- New Provider or Backend, Cloud SaaS, billing, marketplace operation, or
  distributed runtime.
- Autonomous AI execution, automated workflow changes, or automatic approval.

## Target outcome

v5.0 produces an implementation-ready consolidation roadmap. It does not by
itself authorize runtime changes. Any implementation must be admitted through
an additive issue, contract-equivalence evidence, and workflow-invariant tests.

