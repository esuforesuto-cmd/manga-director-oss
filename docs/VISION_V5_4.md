# v5.4 Vision: Creative Quality Framework

## Vision update

v5.4 defines the **Creative Quality Framework**: a single, evidence-oriented
planning model for quality management, review support, validation, and release
judgment. It turns existing evidence into a clear human decision packet; it
does not become an execution engine or replace any authority.

## Product mission

Make the reason a creative deliverable is ready, blocked, or needs review
visible to creators and release owners. Every conclusion must be traceable to
declared policy, supplied evidence, and an explicit owner.

## Design principles

- **StateMachine remains authoritative.** The framework cannot create,
  transition, skip, or approve workflow states.
- **One-page invariant.** Quality planning never broadens a request beyond one
  workflow Page.
- **Evidence before recommendation.** Missing evidence is a visible finding,
  never a guessed success or automatic repair.
- **Human decision boundary.** Recommendations cannot approve pages, releases,
  publication, or configuration changes.
- **Local and additive.** DTOs and reports are presentation-neutral and retain
  legacy-only operation without migration.

## Non-goals

v5.4 does not implement automatic review or approval, workflow mutation,
release publishing, CI/CD control, provider/backend changes, Cloud services,
model training, or a Core Architecture rewrite.

## Long-term direction

The proposed Quality Plane can later consume normalized read-only evidence from
the Review, Testing, CI/CD, and Governance modules. It returns transport-neutral
quality and release recommendations to existing CLI, FastAPI, MCP, and Web UI
adapters only when a separately approved iteration adds those adapters.

## Migration strategy

v5.3.0 remains the baseline. Future quality metadata is optional and attached
at the edge; existing project, repository, workflow, public API, and extension
contracts remain unchanged. See [the migration strategy](MIGRATION_V5_3_TO_V5_4.md).
