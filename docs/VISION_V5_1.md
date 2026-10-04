# v5.1 Vision: Composable Creative Platform

## Vision update

v5.1 evolves One Creative Platform into a **Composable Creative Platform**.
The v5.0 LTS platform stays the stable, supported baseline; v5.1 defines
optional, independently understandable compositions of its existing
capabilities. It creates no new source of truth and requires no new runtime,
API, or storage model.

## Mission

Make existing creative, operational, and enterprise capabilities easier to
discover, select, package, and reuse while preserving every v5.0 public
contract and every domain workflow safeguard.

## Design principles

1. **LTS first.** v5.0 APIs, workflows, persistence, and deployment paths
   remain valid throughout v5.1.
2. **Additive composition.** Modules and Feature Packs declare optional
   capabilities; they neither replace existing services nor import Core state.
3. **Explicit contracts.** Capabilities declare identifiers, dependencies,
   owners, compatibility ranges, and explanations.
4. **Declarative profiles.** A Platform Profile describes an intended
   composition; it never loads code, invokes services, or changes configuration.
5. **Advisory templates.** Solution Templates provide reviewed starting shapes,
   never autonomous workflows or approvals.
6. **Workflow integrity.** The StateMachine remains the only transition
   authority: one execution creates exactly one Page, stages cannot be skipped,
   image generation requires a persisted storyboard, and approval requires a
   completed quality review.

## Non-goals

- Core, StateMachine, WorkflowEngine, Repository, or Unified Runtime redesign.
- Removing, renaming, or redirecting v5.0 Python API, CLI, FastAPI/REST, MCP,
  Web UI, Extension SDK, Provider, or Backend contracts.
- Dynamic module loading, marketplace publication, Cloud SaaS, billing,
  federation, distributed runtime, automatic routing, or autonomous execution.

## Target outcome

The v5.1 plan is issue-ready and implementation-ready only after
contract-equivalence and workflow-invariant evidence prove that v5.0 LTS stays
unchanged.
