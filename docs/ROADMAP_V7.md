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
- merged PR #17 as the verified V7-01 implementation evidence.

### Completion evidence

PR #17, `feat(api): add local workflow HTTP adapter`, was merged into `v7-dev`
on 2026-10-13 as merge commit `097a80d786f494063492eaa871deef6bbf5ab169`.
The retargeted PR passed all required Python, Windows, Web, security, package,
compatibility, and documentation checks, and its independent review found no
P0 or P1 issues. `main` remained unchanged at
`b0291437af05fe53454843ba95fdf88216700f7c`; no version, release, tag,
publication, branch-setting, or I02 change was included.

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

## V7-02 — Real Local Delivery End-to-End Gate

### Planning status

Authorized and in progress. This entry is the bounded Planning Draft and Issue
Specification for V7-02 implementation and validation. It does not authorize
release or publication.

### Objective

Prove that the existing Web UI and the V7-01 loopback HTTP adapter work
together through the real local Application, `WorkflowEngine`, StateMachine,
and `LocalFileRepository` boundaries in one deterministic end-to-end quality
gate. The gate must add verification only, not new product behavior.

### Scope

- add a dedicated browser end-to-end mode that starts the real
  `manga-director api serve` command and the existing Next.js Web UI on
  loopback interfaces;
- use an isolated temporary configuration, repository root, and the existing
  mock Providers so the scenario needs no credentials or external network;
- exercise one Page from Project creation through `QualityChecked` and
  explicit human approval, using only actions supplied by the real API;
- verify the persisted approved result after a browser refresh or a fresh read;
- run the real-delivery browser scenario as a required Linux CI gate while
  retaining the existing mock-API browser test for fast presentation feedback;
- document the local command, isolation behavior, and failure diagnostics.

### Inputs

- completed V7-01 Workflow HTTP Adapter and its accepted invariants;
- [RFC-V7-001: Local Workflow HTTP Delivery](RFC_V7_001_LOCAL_WORKFLOW_HTTP_DELIVERY.md);
- the existing FastAPI CLI entry point, Web API client, Playwright setup,
  `LocalFileRepository`, and mock Provider implementations;
- the current Python, Web, LocalFile security, compatibility, and package
  quality gates.

### Outputs

- a deterministic real-API Playwright scenario separate from the mock-API
  scenario;
- minimal process and temporary-state orchestration owned by test tooling;
- a required CI invocation for the real local delivery gate;
- synchronized Web UI, HTTP API, and troubleshooting documentation.

### Acceptance criteria

- The browser communicates with the real FastAPI adapter; the test does not
  substitute `web/e2e/mock-api.mjs` for this scenario.
- The API and Web UI bind only to documented loopback addresses and use an
  isolated temporary repository root.
- The scenario creates exactly one Page, follows API-provided actions without
  skipping or reversing a state, and persists storyboard data before image
  generation.
- Approval is unavailable before persisted `QualityChecked`, requires a
  non-empty human identity, and produces an `Approved` Page that remains
  observable after refresh or a fresh read.
- The scenario uses existing mock Providers and performs no external model,
  Marketplace, or credentialed network request.
- Test orchestration terminates child processes and removes temporary test
  state on success and failure.
- The existing mock-API browser test remains available and passes.
- No runtime endpoint, HTTP DTO, Domain model, StateMachine rule, CLI or MCP
  contract, Provider selection rule, or public import changes.
- No new runtime or development dependency, Project DELETE, auto-approval,
  auto-retry, parallel execution, remote exposure, or I02 surface.
- The implementation stays within an approved allowlist and passes the
  required Python, Web, browser, compatibility, security, package, and
  whitespace checks.

### Out of scope

- new workflow actions, endpoints, DTO fields, or Web UI features;
- a combined production launcher or installer for the API and Web UI;
- cloud deployment, remote access, authentication, OAuth, or JWT;
- Provider changes, live model calls, automatic Provider switching, or
  Marketplace behavior;
- Project deletion, automatic approval, automatic retry, autonomous or
  parallel execution;
- StateMachine, persistence-format, version, release, tag, package metadata,
  publication, default-branch, ruleset, or I02 changes.

### Dependencies

- V7-01 remains complete and unchanged on `v7-dev`.
- Existing optional API and Web development dependencies are sufficient; a
  dependency or lockfile change requires a revised plan and separate review.
- The CI runner can install the already-declared Playwright Chromium runtime.

### Validation

- `ruff check .`;
- the repository's current Linux and Windows `mypy` gates;
- focused HTTP/Application tests and the full applicable `pytest` regression;
- `npm run lint`, `npm run typecheck`, `npm run test`, and `npm run build`;
- existing mock-API Playwright E2E and the new real-API Playwright E2E;
- LocalFile path-containment and Windows LocalFile security regression;
- `pip-audit --strict .` and `npm audit --omit=dev --audit-level=high`;
- package/public-contract checks already required by CI;
- exact changed-file allowlist review and `git diff --check`.

### Estimated complexity

Medium. The product behavior is unchanged, but deterministic startup,
readiness, cleanup, temporary persistence, and CI process ownership cross the
Python and Web test boundaries.

### Architecture notes

The new orchestration belongs to test tooling only. Production Web components
continue to call the typed REST client; FastAPI remains a Presentation adapter;
the Application service, `WorkflowEngine`, StateMachine, repository ports, and
Provider composition retain their existing authority. The real-delivery test
must invoke public local entry points instead of importing Web code into Python
or duplicating workflow decisions in its harness.

### Authorization gate

The approved V7-02 scope authorizes the bounded implementation, commit, push,
pull request, CI, read-only review, in-scope P0/P1 remediation, and merge to
`v7-dev` when every required condition passes. `main`, versioning, release,
tag, publication, branch deletion, force-push, settings, and I02 remain out of
scope.

## Epic 1 sequencing

| Issue | State | Dependency | Completion evidence |
| --- | --- | --- | --- |
| V7-01 Workflow HTTP Adapter | Complete | Accepted RFC-V7-001 and explicit v7 implementation authorization | PR #17 merged into `v7-dev` at `097a80d`; required CI passed; P0/P1 = 0; `main` unchanged |
| V7-02 Real Local Delivery End-to-End Gate | In progress | Completed V7-01 and explicit approval of the bounded V7-02 Planning Draft | Implementation and validation in progress on the approved seven-file allowlist |

No later Epic 1 implementation is authorized solely by this roadmap.
Additional issues must be proposed with their own bounded scope, compatibility
analysis, validation plan, and approval state.

## Epic quality gates

Every Epic 1 change requires architecture-boundary, backward-compatibility,
workflow-invariant, LocalFile security, and delivery-contract review. P0 or P1
findings block merge. Documentation acceptance does not establish release
readiness, and release readiness does not authorize publication.
