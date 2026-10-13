# RFC-V7-001: Local Workflow HTTP Delivery

- Status: Accepted; V7-01 implemented on `v7-dev`
- Target line: v7.0 Discovery (Post-LTS)
- Related roadmap items: V7-01 Workflow HTTP Adapter and V7-02 Real Local
  Delivery End-to-End Gate
- Implementation evidence: PR #17 merged into `v7-dev`

## Decision boundary

The `6.0.x` line remains LTS, and `main` remains the LTS stability line. New
feature discovery is assigned to the Post-LTS v7.0 Discovery line so that it
does not expand the v6 LTS maintenance contract. The v7 designation separates
new feature work from v6 LTS; it does not imply an intention to introduce
breaking changes.

Acceptance of this RFC authorizes an implementation proposal only. It does not
authorize a merge to `main`, a version change, a release, a tag, package
publication, or any other deployment or distribution action.

## Problem

The repository already contains an independent Web UI and established local
workflow capabilities, but the browser has no approved local delivery boundary
through which it can use the current Manga Director workflow. Direct browser
access to Python internals would duplicate workflow decisions and cross the
Presentation, Application, and Domain boundaries. Adding new feature behavior
to the v6 LTS line would also conflict with its maintenance-only scope.

The first v7 product objective is therefore a safe, local HTTP delivery adapter
that connects the existing Web UI to the current Manga Director workflow while
preserving all existing execution and compatibility authorities.

## Goals

- Define an optional, loopback-only HTTP delivery boundary for the existing
  Web UI and current workflow capabilities.
- Keep `StateMachine` as the sole transition authority and `WorkflowEngine` as
  the execution authority.
- Preserve exactly one Page per execution, storyboard persistence before image
  generation, and `QualityChecked` before approval.
- Require explicit human approval; an adapter must never infer or automate it.
- Preserve provider-neutral workflow and Application contracts.
- Preserve v5/v6 public compatibility, including existing Python, CLI, MCP,
  Web UI, Repository, SDK, Plugin, and StateMachine contracts.
- Preserve `LocalFileRepository` path containment, validation, and safe error
  behavior at the HTTP boundary.
- Use dedicated HTTP presentation DTOs so Domain models are not exposed as the
  wire contract.

## Non-goals

The initial v7 scope does not include:

- cloud deployment or remote network exposure;
- OAuth, JWT, or an internet-facing API;
- automatic approval or automatic retry;
- autonomous, concurrent, or parallel workflow execution;
- any `StateMachine` transition or state change;
- automatic Provider switching;
- Marketplace network behavior;
- a Project DELETE API;
- I02 or any work that would authorize I02;
- a breaking migration or intentional v5/v6 incompatibility;
- version, release, tag, package metadata, or publication changes.

## Proposed architecture

```text
Existing Web UI
      |
      v
Optional loopback HTTP adapter and HTTP DTOs
      |
      v
Transport-neutral Application service
      |
      v
WorkflowEngine and repository ports
      |
      v
StateMachine and existing infrastructure authorities
```

The adapter is a Presentation-layer boundary. It maps HTTP requests and
responses to a transport-neutral Application service, which delegates workflow
execution to the existing `WorkflowEngine`. The adapter must not import or call
Agents directly, select Providers, decide transitions, or contain a second
workflow implementation. CLI and MCP remain peer delivery mechanisms and keep
their existing call and import contracts.

Read operations must remain read-only: they must not save Repository data,
transition workflow state, execute Agents, or construct Providers. Mutating
operations must load and save through the existing repository boundary and may
advance only one Page through the existing workflow authority.

## Affected public contracts

RFC acceptance changes no public contract by itself. A future V7-01
implementation proposal may add the following optional surface:

- a local HTTP server entry point;
- dedicated, versioned HTTP request and response DTOs;
- local workflow endpoints required by the existing Web UI;
- safe HTTP status and error mappings for expected failures.

The following contracts must remain unchanged unless a separate approved RFC
explicitly says otherwise:

- the v5/v6 Python import and call surfaces;
- CLI command names, arguments, behavior, and exit semantics;
- MCP tool names, schemas, imports, call forms, and local stdio behavior;
- `StateMachine`, `PageState`, and transition rules;
- `WorkflowEngine` execution semantics;
- repository ports and `LocalFileRepository` security guarantees;
- Provider interfaces and selection ownership;
- the existing Web UI's presentation-layer ownership.

HTTP DTOs are additive delivery contracts and must not become replacements for
Domain models or alter the CLI/MCP contracts.

## Compatibility analysis

The proposal is compatible when the adapter is optional and additive, all
workflow decisions continue to be made by the existing authorities, and the
v5/v6 surfaces continue to pass their regression suites unchanged. Selecting
v7 provides a development boundary for the feature; it is not permission to
break compatibility.

The implementation must preserve these observable invariants:

1. An execution operates on exactly one Page.
2. No stage is skipped or reversed.
3. A storyboard is persisted before image generation.
4. Approval is legal only from `QualityChecked`.
5. Approval contains explicit human evidence.
6. Provider choice remains outside workflow and delivery logic.
7. CLI and MCP behavior remains compatible.
8. Local-file project identifiers and paths cannot escape the configured root.

PR #17 is the technically verified V7-01 implementation and is merged only on
the Post-LTS `v7-dev` line. It remains unmerged into `main`. This RFC does not
authorize promotion to `main`, versioning, release, tag, or publication.

## Alternatives considered

### Merge the candidate directly into the v6 LTS line

Rejected. A new workflow delivery surface is feature work and is outside the
maintenance-only v6 LTS contract.

### Keep browser workflow access unsupported

Rejected as the first v7 product direction. The existing Web UI requires a
bounded local transport to use the current workflow without importing Python
internals or duplicating workflow rules.

### Put workflow logic in the Web UI or HTTP adapter

Rejected. This would duplicate `StateMachine` and `WorkflowEngine` authority,
increase compatibility risk, and make cross-delivery behavior inconsistent.

### Reuse MCP as the browser transport

Rejected for the initial design. MCP remains a compatible local stdio delivery
surface; using its presentation DTOs or transport as the Web contract would
couple two delivery mechanisms and destabilize the existing MCP surface.

### Begin with a remote or cloud API

Rejected. Remote exposure introduces authentication, authorization, transport,
deployment, and threat-model requirements that are unnecessary for the first
local product objective.

## Migration and rollback

No v6 data, public API, or package migration is authorized by this RFC. A
future implementation must be additive and optional. Existing CLI, MCP, Python,
and repository workflows remain the default compatible paths.

Before release, rollback consists of disabling or removing the optional HTTP
composition and Web UI connection while retaining the unchanged Application,
Workflow, Domain, and Repository authorities. Planning-only rollback consists
of reverting this RFC and its roadmap entry. Any later persistent-data or
public-contract migration requires a separate approved proposal with explicit
forward and reverse steps.

## Validation plan

A V7-01 implementation proposal must provide executed evidence for:

- exact transition-table and invalid-transition regression tests;
- one-Page execution and `QualityChecked` approval-gate tests;
- storyboard-before-generation and explicit-human-approval tests;
- HTTP DTO, endpoint, status-code, and safe-error tests;
- read-only GET behavior and absence of Provider construction on reads;
- CLI and MCP compatibility regression tests;
- local-file path-containment and Windows LocalFile security tests;
- loopback binding and restricted-origin behavior;
- absence of Project DELETE, auto-approve, auto-retry, autonomous execution,
  and parallel execution surfaces;
- Python lint, type checking, and full applicable regression tests;
- Web lint, type checking, tests, and production build;
- dependency and security audit evidence for any separately approved
  dependency change;
- package and public-contract checks when package contents are affected;
- `git diff --check` and exact changed-file review against the authorized
  implementation allowlist.

PR #17 may be used as candidate evidence for these checks. Its evidence must be
revalidated against the authorized v7 base and scope before any merge decision.

## V7-02 verification continuation

V7-02 adds a real local delivery end-to-end quality gate for the accepted
V7-01 boundary. It starts the existing loopback-only API and Web UI with an
isolated temporary `LocalFileRepository` and existing mock Providers, then
verifies one Page through `QualityChecked` and explicit human approval. This is
verification-only work: it adds no endpoint, DTO, workflow action, Provider,
runtime dependency, remote exposure, automatic approval, Project DELETE, or
I02 behavior.

The existing mock-API browser scenario remains the fast Presentation test. The
V7-02 scenario separately proves that the real HTTP adapter, Application
service, `WorkflowEngine`, StateMachine, and persistence boundary compose
without duplicating their decisions in test tooling.

Run the real local gate from `web/` after installing the repository with the
existing `api` extra and installing Playwright Chromium:

```console
npm run test:e2e:real
```

The test runner starts both services on `127.0.0.1`, creates a unique temporary
configuration and repository root, and removes that state when the API helper
exits. It uses the offline profile and existing mock Providers, so credentials
and external model access are neither required nor permitted by this gate.

On failure, Playwright retains a trace under `web/test-results/`. Review that
trace together with the API server output to distinguish a browser readiness
or refresh failure from an HTTP or persisted-workflow failure. A local bind
failure on port 3000 or 8000 must be resolved before retrying; it is not a
workflow result.

## Security considerations

- Bind only to the loopback interface; do not permit a host override that
  enables remote exposure in the initial implementation.
- Restrict browser origins to the documented local development origins.
- Do not add authentication as a substitute for local-only containment; OAuth,
  JWT, and internet exposure remain out of scope.
- Validate and normalize all identifiers and DTOs before Application calls.
- Preserve `LocalFileRepository` root containment and reject traversal,
  absolute-path, symlink/reparse-point, and unsafe-name escapes as required by
  the existing platform contract.
- Return stable, minimal errors without tracebacks, prompts, filesystem paths,
  credentials, or other sensitive internals.
- Keep read endpoints free of Repository writes, transitions, Agent execution,
  and Provider construction.
- Expose no Project DELETE route and no implicit destructive operation.
- Require explicit approval identity and the persisted `QualityChecked` state.
- Keep test and default operation independent of live network credentials.

## Documentation impact

RFC acceptance requires only this RFC and `ROADMAP_V7.md`. A separately
authorized V7-01 implementation proposal must update the affected architecture,
HTTP API, Web UI, public API, installation, troubleshooting, compatibility, and
security documentation identified by its final diff. Release notes, migration
guides, version metadata, and package publication material remain outside this
RFC and require separate authorization.

## Acceptance criteria

This RFC may be accepted when reviewers confirm that it:

- keeps `6.0.x` and `main` as the LTS stability line;
- defines v7.0 Discovery as a compatible Post-LTS development line;
- establishes safe local HTTP delivery as the first product objective;
- preserves all workflow, compatibility, Provider, MCP/CLI, and LocalFile
  authorities listed above;
- contains no authorization for I02, release, versioning, or publication; and
- treats PR #17 only as unmerged candidate evidence for V7-01.
