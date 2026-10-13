# v7 Development Roadmap

## Planning baseline

The `6.0.x` line remains LTS, and `main` remains the LTS stability line. v7.0
Discovery is the Post-LTS development line for new feature proposals that do
not belong in v6 LTS maintenance. The v7 designation separates new feature
work from v6 LTS; it does not signal an intention to introduce breaking
changes.

This roadmap is a planning artifact. It does not change the installed version,
authorize a release, change package metadata, or authorize tag or package
publication. Work enters `main` only through its separately approved and
validated change process.

## Epic 1 — Local Workflow Delivery

### Objective

Connect the existing Web UI to the current Manga Director workflow through a
safe, optional, local HTTP delivery boundary while retaining all established
Domain, Application, workflow, repository, and delivery authorities.

### Required invariants

- `StateMachine` remains the sole transition authority.
- `WorkflowEngine` remains the execution authority.
- Each execution processes exactly one Page.
- Storyboard persistence precedes image generation.
- Approval requires persisted `QualityChecked` state and explicit human
  approval evidence.
- Workflow and delivery remain Provider-neutral.
- v5/v6 Python, CLI, MCP, Web UI, Repository, SDK, Plugin, and StateMachine
  compatibility is preserved.
- `LocalFileRepository` security and configured-root containment are preserved.

### Initial non-goals

- cloud or remote exposure;
- OAuth, JWT, or an internet-facing API;
- automatic approval or automatic retry;
- autonomous or parallel execution;
- `StateMachine` changes;
- automatic Provider switching;
- Marketplace network behavior;
- a Project DELETE API;
- I02;
- a breaking migration;
- version, release, package metadata, tag, or publication changes.

## V7-01 — Workflow HTTP Adapter

### Outcome

Provide the existing Web UI with an optional loopback-only HTTP adapter that
maps dedicated HTTP DTOs to a transport-neutral Application service. The
Application service delegates workflow execution to the existing
`WorkflowEngine` and persistence to existing repository ports. HTTP must not
own transitions, call Agents directly, select Providers, or change CLI/MCP
contracts.

### Inputs

- [RFC-V7-001: Local Workflow HTTP Delivery](RFC_V7_001_LOCAL_WORKFLOW_HTTP_DELIVERY.md)
- the existing Web UI client and presentation contracts;
- current Workflow, StateMachine, Repository, CLI, and MCP contracts;
- PR #17 as technically verified implementation candidate evidence.

### Candidate evidence

PR #17, `feat(api): add local workflow HTTP adapter`, is the initial
implementation candidate for V7-01. Its current implementation and successful
CI may be reviewed and reused as evidence after v7 implementation authorization.
It remains unmerged into `main`; this roadmap does not modify, close, retarget,
or merge it and does not grant that authorization.

### Acceptance criteria

- The server is local-only and cannot be configured for remote exposure in the
  initial scope.
- Dedicated HTTP DTOs prevent Domain models from becoming the wire contract.
- Read endpoints do not save Repository data, transition state, execute Agents,
  or construct Providers.
- Mutating endpoints preserve the one-Page execution and transition rules.
- Approval requires `QualityChecked` and explicit human approval evidence.
- No Project DELETE, auto-approve, auto-retry, autonomous execution, parallel
  execution, Provider auto-switching, Marketplace network, or I02 surface is
  introduced.
- Existing Python, CLI, MCP, Web UI, Repository, SDK, Plugin, StateMachine, and
  LocalFile compatibility/security regressions pass.
- Applicable Python and Web quality checks, full regression, security checks,
  package checks, and `git diff --check` pass.
- The final implementation diff and documentation match an explicitly
  authorized v7 allowlist.

### Authorization gate

Acceptance of RFC-V7-001 authorizes an implementation proposal only. V7-01
implementation, merge, versioning, release, tag, and publication decisions are
separate gates. No roadmap entry authorizes I02.

## Epic 1 sequencing

| Issue | State | Dependency | Completion evidence |
| --- | --- | --- | --- |
| V7-01 Workflow HTTP Adapter | Discovery | Accepted RFC-V7-001 and explicit v7 implementation authorization | Authorized implementation diff, compatibility review, executed quality/security gates, and merge decision |

No later Epic 1 issue is authorized by this initial roadmap. Additional issues
must be proposed with their own bounded scope, compatibility analysis,
validation plan, and approval state.

## Epic quality gates

Every Epic 1 change requires architecture-boundary, backward-compatibility,
workflow-invariant, LocalFile security, and delivery-contract review. P0 or P1
findings block merge. Documentation acceptance does not establish release
readiness, and release readiness does not authorize publication.
