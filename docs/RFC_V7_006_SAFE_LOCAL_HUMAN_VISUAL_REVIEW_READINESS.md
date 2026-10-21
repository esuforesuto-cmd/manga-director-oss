# RFC-V7-006: Safe Local Human Visual Review and Approval Readiness

- Status: Design approved; V7-08 implementation complete and verified on `v7-dev`
- Implementation evidence: PR #36 final head
  `df2b6fdae559de9c5ca7e0a59dfc12fa2fad28cd` merged into `v7-dev` at
  `ea45c7ef525198b2f77c236dced7742ee06857e1`; post-merge checks passed 13/13,
  CodeQL passed 3/3, and independent review reported P0/P1/P2 = 0/0/0.
- Target line: v7.0 Discovery (Post-LTS)
- Roadmap item: V7-08 Safe Local Human Visual Review and Approval Readiness
- Delivery scope: docs-only design
- Decision owner: an explicit local human reviewer

## Decision boundary

This RFC freezes the smallest loopback-only review surface that connects the
exact Page-bound PNG presentation delivered by V7-07 to the advisory human
visual QA and approval-readiness evaluator delivered by V7-06.

The surface accepts an explicit, transient human visual judgment for one
existing Project and Page, reconstructs the authoritative evidence chain on
the server, and returns one redacted `ready`, `needs_review`, or `blocked`
assessment. It does not persist the judgment, modify the Project or Page,
execute quality review, approve the Page, or make readiness an approval
precondition. The existing explicit approval action and `StateMachine` remain
the only approval authority.

This RFC adds no implementation. It authorizes no endpoint, Web form, public
Python export, persistence format, migration, live generation, or Provider
operation.

## Problem

V7-06 provides a private, deterministic service that can bind exact generation
and workflow evidence, an advisory Visual Continuity QA report, and a supplied
human visual judgment into an approval-readiness result. It intentionally has
no HTTP or Web surface and performs no asset access or persistence.

V7-07 lets the loopback Web UI display the exact registered PNG already bound
to one Page. It intentionally does not collect human judgment, calculate
readiness, persist review evidence, or affect approval.

The current Web UI therefore places a generated image near the existing
quality and approval controls without a safe bridge for a human to record a
bounded visual judgment and see the V7-06 advisory result. A future bridge
must not let browser input choose an attempt, asset, provenance record, path,
digest, Provider, QA report, or approval target. It must also avoid implying
that loading an image, submitting a checklist, or receiving `ready` is an
approval or a persisted audit record.

## Planning summary

- **Title:** V7-08 Safe Local Human Visual Review and Approval Readiness
- **Objective:** Add a separately approvable, loopback-only, non-persistent
  human-review surface that binds reviewer-authored judgment to the exact
  server-resolved Page evidence and returns V7-06 advisory readiness.
- **Scope:** One existing Project, one existing Page, the exact V7-07 image,
  authoritative read-only generation and workflow evidence, one explicit
  human checklist submission, and one transient readiness result.
- **Inputs:** Project ID and positive Page number from the route plus bounded
  reviewer identity, caller-supplied review timestamp, closed checklist
  outcomes and rationales, overall judgment, and overall rationale.
- **Outputs:** A redacted, non-cacheable `ready`, `needs_review`, or `blocked`
  response with ordered findings and missing prerequisites.
- **Dependencies:** Completed V7-06 and V7-07, the existing loopback workflow
  HTTP/Web boundary, LocalFile ownership, Workflow Application Ledger,
  generation evidence, repository workflow consistency, and existing explicit
  quality and approval actions.
- **Estimated complexity:** Medium for a separately approved implementation;
  Low for this docs-only design.
- **Architecture notes:** One additive read-only POST application path. Browser
  input contains human judgment only; evidence identity is reconstructed and
  bound on the server. No persistence, transition, Provider, or approval
  authority is added.

## Goals

- Let a local human inspect the exact V7-07 image and explicitly submit a
  complete visual checklist for the selected Page.
- Derive all attempt, asset, provenance, QA, workflow, and storage authority
  from existing server-side state rather than browser input.
- Reuse the V7-06 closed judgment vocabulary and readiness precedence without
  weakening its evidence requirements.
- Keep the assessment transient, deterministic for canonical inputs,
  redacted, non-cacheable, and visibly advisory.
- Preserve the existing quality action, approval form, approval endpoint,
  `StateMachine`, `WorkflowEngine`, and public compatibility.
- Fail closed without generation, retry, fallback, repair, mutation, or
  automatic approval.

## Non-goals

- persisting, updating, deleting, listing, or recovering human review records;
- making readiness mandatory for, equivalent to, or an input to the existing
  explicit approval action;
- automatically running quality review, advancing to `QualityChecked`, calling
  approval, filling `approvedBy`, or changing Page state;
- accepting browser-selected attempt, asset, provenance, QA report, digest,
  storage name, path, root, Provider, URI, URL, or arbitrary metadata;
- changing existing Page detail JSON, workflow action DTOs, approval DTOs,
  StateMachine states, commands, events, or persistence schemas;
- public Python exports, CLI, MCP, SDK, Plugin, Provider, or remote API
  surfaces;
- authentication, authorization, reviewer roles, signatures, attestations,
  notification, routing, escalation, or multi-reviewer consensus;
- image annotation, cropping, thumbnails, conversion, upload, download, or
  arbitrary-file browsing;
- live generation, regeneration, retry, recovery execution, or Provider
  switching;
- I02, dependency or lockfile changes, `main`, versioning, release, tag,
  publication, Settings, force push, history rewriting, or branch deletion.

## Source contracts

The design composes existing contracts without replacing them:

- V7-07 `GET /projects/{project_id}/pages/{page_number}/generated-asset`
  remains the only image-byte presentation route and remains responsible for
  exact Page-to-ledger-to-evidence-to-owner-to-opened-bytes validation.
- `HumanVisualQAApprovalReadinessService` remains the private canonical
  evaluator for `ready`, `needs_review`, and `blocked`.
- `VisualContinuityQAService` remains advisory and compares structured logical
  evidence only; it does not inspect image bytes or record human judgment.
- the existing persisted Page and repository workflow history remain the
  authority for current state and legal actions.
- the existing quality action remains the only path to `QualityChecked`.
- the existing explicit approval action remains the only path from
  `QualityChecked` to `Approved` and still requires explicit human identity.
- LocalFile ownership, configured-root containment, ordinary-file identity,
  byte limit, SHA-256, and strict PNG validation remain authoritative for the
  image under review.

Neither V7-06 readiness nor V7-07 presentation is renamed or reinterpreted.
V7-08 is a delivery adapter over those completed boundaries.

## Frozen architecture

### Additive local route

The separately approved V7-08 implementation added exactly one logical
operation:

`POST /projects/{project_id}/pages/{page_number}/visual-review-readiness`

The route is available only through the existing loopback workflow API and
inherits its exact-origin CORS policy. It must not be exposed on a Provider,
remote, LAN, wildcard, CLI, MCP, SDK, or Plugin surface.

The path supplies the only Project and Page selectors. Query parameters are
rejected. The request body is required because it carries the explicit human
judgment, but it carries no evidence selector or filesystem authority.

### Request contract

The request contains only:

- `reviewerId`: one bounded nonblank logical local reviewer reference;
- `reviewedAt`: one timezone-aware caller-supplied timestamp;
- `checklist`: exactly one decision for every V7-06 human visual criterion;
- `overallJudgment`: `acceptable_for_approval_consideration`,
  `further_review_required`, or `blocked`; and
- `rationale`: bounded nonblank human-authored text.

Each checklist entry contains only:

- one closed V7-06 criterion;
- one `acceptable`, `needs_review`, `blocked`, or `not_applicable` outcome;
  and
- bounded nonblank rationale.

The complete criterion set remains:

- character identity, face, costume, props, pose, gaze, emotion, and screen
  direction;
- location, time, composition, and panel intent;
- visible corruption, truncation, watermark, unsafe content, and unintended
  text; and
- continuity comparison.

Only the optional `props` and `continuity_comparison` criteria may use
`not_applicable`, matching V7-06. Missing, duplicate, unknown, or conflicting
criteria fail closed. Extra request fields are forbidden.

The request must reject `projectId`, `pageNumber`, `pageId`, `reviewId`,
`attemptId`, `assetId`, `outputAssetId`, `provenanceReference`,
`qaReportReference`, `provider`, `digest`, `path`, `storageName`, `root`, `uri`,
`url`, `approvedBy`, workflow actions, and arbitrary metadata.

Reviewer identity and rationale are evidence, not credentials. They must not
contain a path, URL, email address, secret-like value, control characters, or
unbounded text. The server does not authenticate, authorize, or reuse
`reviewerId` as `approvedBy`.

### Server-owned evidence resolution

On explicit submission, the server resolves the exact evidence chain from the
route and existing persisted state:

~~~text
Project + Page route
        |
        v
persisted logical Generated artifact and current Page state
        |
        v
Workflow Application Ledger applied proof
        |
        v
exact generation evidence / attempt / provenance / output binding
        |
        v
LocalDurableAssetOwner exact registered PNG validation
        |
        v
canonical advisory Visual Continuity QA from existing logical Page evidence
        |
        v
server-bound transient human judgment
        |
        v
V7-06 readiness: ready | needs_review | blocked
~~~

The browser cannot select or override any internal edge. Exactly one matching
Page, applied ledger row, generation attempt, output asset, provenance record,
owner registry row, and safe PNG must exist. Duplicate, missing, ambiguous,
corrupt, stale, or mismatched state fails closed.

The server creates any request-local review and QA logical references
deterministically from canonical non-secret inputs. Those references provide
binding only; they are not persisted identifiers, authorization tokens, cache
validators, filesystem names, or approval identities.

### Read-only Visual QA construction

The implementation may construct advisory Visual Continuity QA only from
existing persisted logical Page, storyboard, review, generation, and workflow
evidence. It must not accept replacement logical evidence from the browser,
infer missing artistic facts, or select a "latest" attempt or output.

An existing exact prior-panel reference may be followed only when it is
already present and unambiguous. The implementation must not select a
neighboring Page merely from filesystem or repository order. Missing optional
continuity evidence remains `not_applicable` or `needs_review` according to the
existing closed V7-06/V7 Visual QA rules; it never defaults to acceptable.

The reconstructed report must round-trip through the existing canonical
`VisualContinuityQAService`. If existing state cannot supply a structurally
valid report, the assessment is redacted `needs_review` or `blocked`; no state
is created or repaired.

### Exact asset validation

Readiness submission must independently prove that the reviewed Page still
resolves to the safe V7-07 image. It reuses the same LocalFile authority and
same-opened-bytes containment, identity, size, SHA-256, and strict PNG
validation. The assessment response contains no image bytes.

The Web UI continues loading image bytes only from the fixed V7-07 route built
from Project ID and Page number. It must not create a path, URL, data URL,
asset selector, attempt selector, or Provider selector from metadata.

### Page-state behavior

- `Generated`: the image and review form may be presented, but V7-06 readiness
  cannot exceed `needs_review` because persisted quality review is incomplete.
- `QualityChecked`: a complete, acceptable, exact evidence package may return
  advisory `ready`.
- `Approved`: V7-08 does not reopen or reassess the Page. Historical approval
  remains authoritative and the review submission fails closed.
- any earlier state: the Page has not reached the visual-review boundary and
  the operation fails closed.

No request runs the quality action or changes these states.

### Response contract

A valid assessment response contains only:

- `status`: `ready`, `needs_review`, or `blocked`;
- `ready`: the matching boolean;
- `pageState`: the persisted Page state used by the assessment;
- deterministic ordered redacted findings;
- deterministic ordered missing-prerequisite codes; and
- `analysisOnly: true`.

The response must not include reviewer identity, reviewer rationale, raw
checklist text, Page artifacts, attempt ID, asset ID, provenance reference, QA
reference, Provider metadata, digest, byte length, registry values, storage
name, filesystem path, URI, URL, image bytes, `approvedBy`, next state, or a
workflow command.

Both successful and fail-closed JSON responses use `Cache-Control: no-store`
and `X-Content-Type-Options: nosniff`. They emit no ETag, Last-Modified,
Location, redirect, download filename, or cache validator. Error details are
redacted and preserve the existing HTTP error envelope.

### Transient Web behavior

The local Page view may show a human visual review form only for a Page whose
state and exact logical image descriptor already qualify for V7-07 display.
The form must label the assessment as advisory and not saved.

- loading or refreshing the Page creates no judgment or readiness result;
- image load success does not create a favorable checklist outcome;
- every checklist decision requires explicit human input;
- submitting the form performs one assessment and displays its transient
  result in the current client state;
- refresh, navigation, or a new submission discards the prior client result;
- `ready` does not auto-fill, call, enable, hide, replace, or gate the existing
  approval form; and
- `reviewerId` is never copied into `approvedBy`.

The existing approval form remains controlled only by existing persisted Page
state and `approvalRequired`. V7-08 introduces no new workflow action.

### No persistence or mutation

The POST operation is computational despite carrying a request body. It must
not create or update:

- Project or Page files;
- Page state, history, artifacts, quality, continuity, or approval fields;
- review, readiness, decision, audit, cache, session, temporary, or access-log
  records;
- ledger, evidence, registry, repository, or sidecar databases;
- directories, WAL/SHM/journal files, migration markers, or repair output; or
- browser-local durable storage.

Before/after filesystem manifests for the bounded repository and sidecar roots
must be equivalent. Normal infrastructure logging must not be added as part of
this feature.

### Read-only storage discipline

All repository and sidecar state is opened through existing read-only paths.
SQLite-backed ledger, evidence, or registry state must already exist and must
be opened with `mode=ro` and query-only semantics after preflight that cannot
create WAL, SHM, or journal files. Missing database, schema mismatch,
unsupported journal state, corruption, or ambiguous rows fail closed without
creation, migration, repair, checkpoint, or cleanup.

The HTTP adapter handles no SQLite connection, filesystem path, registry row,
or Provider metadata. It delegates evidence resolution and assessment to a
transport-neutral private Application service.

### Determinism

For the same canonical persisted state and the same canonical request, the
status, findings, missing prerequisites, request-local references, and response
ordering are identical.

- the server uses the caller-supplied timezone-aware `reviewedAt` and does not
  generate or compare current time;
- checklist and findings use closed vocabularies and stable ordering;
- no filesystem order, locale, random identifier, environment value, DNS,
  network result, Provider result, or browser state affects assessment; and
- repeated submission does not accumulate or overwrite state.

### Security and privacy

- The API remains exact-loopback and current CORS allowlists are unchanged.
- No DNS, proxy, redirect, remote fetch, Provider request, or outbound network
  call is permitted.
- Request size, checklist cardinality, rationale length, and finding count are
  bounded.
- Browser input is data only and never becomes a path, SQL fragment, log
  format, HTML, command, approval identity, or evidence selector.
- Reviewer-authored text is rendered as text and not HTML.
- Errors and responses disclose no internal identity or storage metadata.
- The operation is not authentication, authorization, access control, or a
  durable audit record.

## Failure and recovery semantics

Assessment is fail-closed and read-only.

- malformed or extra input is rejected before evidence access;
- missing, corrupt, unsafe, duplicate, ambiguous, or mismatched authoritative
  state returns a redacted error or `blocked` result;
- incomplete but non-conflicting evidence returns `needs_review`;
- explicit human `blocked` outcomes produce `blocked`;
- explicit `needs_review` outcomes or incomplete quality state cannot produce
  `ready`; and
- no failure path retries, selects a fallback, regenerates, repairs, writes,
  approves, or triggers another workflow action.

Recovery consists only of correcting persisted evidence through a separately
authorized existing workflow or submitting a new explicit human judgment. A
new submission does not modify or erase the prior transient result.

## Public contract compatibility

The separately approved V7-08 implementation added one new loopback HTTP
request and response DTO plus its Web-only form and client call. All existing
JSON DTOs and
routes remain unchanged. Public Python imports and exports remain unchanged.

The design preserves CLI, MCP, SDK, Plugin, Repository, LocalFile, Provider,
generation, quality, continuity, approval, `StateMachine`, `WorkflowEngine`,
v5, v6, and project-readability compatibility. No migration is required.

Any implementation need for an existing DTO change, public Python export,
StateMachine or WorkflowEngine change, persistence field, dependency, remote
surface, reviewer storage, approval coupling, or I02 authority is a scope
expansion and must stop for separate authorization.

## Validation plan

This docs-only change requires:

- exact two-file allowlist:
  `docs/RFC_V7_006_SAFE_LOCAL_HUMAN_VISUAL_REVIEW_READINESS.md` and
  `docs/ROADMAP_V7.md`;
- local Markdown-link resolution and `git diff --check`;
- confirmation that source, tests, dependencies, lockfiles, workflows,
  package metadata, versions, Settings, and `main` are unchanged;
- architecture, authority, privacy, approval-boundary, LocalFile-security,
  public-contract, and compatibility review;
- independent review with P0 = 0 and P1 = 0 before merge; and
- required hosted CI, CodeQL, and post-merge verification.

The separately approved V7-08 implementation additionally required:

- focused positive cases for `Generated` → `needs_review` and exact
  `QualityChecked` evidence plus acceptable judgment → `ready`;
- `blocked`, missing, duplicate, ambiguous, stale, mismatch, malformed,
  partial, unsafe-file, digest, strict-PNG, oversize, and corrupt-sidecar
  rejection;
- rejection of query parameters, extra fields, evidence selectors, paths,
  URLs, secrets, unsafe rationale, incomplete or duplicate checklist, and
  invalid `not_applicable` use;
- proof that request/refresh/repeat assessment creates or repairs nothing with
  equivalent before/after filesystem manifests;
- exact redacted response and no-store/nosniff header tests with no internal
  identifier, path, digest, Provider, reviewer text, redirect, or validator
  leak;
- proof of no quality action, approval, Page mutation, review persistence,
  readiness persistence, Provider, generation, retry, fallback, I02, DNS,
  proxy, or outbound request;
- existing approval-form independence and no reviewer-to-approver copying;
- V7-06, V7-07, HTTP, Web, LocalFile, generation, quality, approval, v5/v6,
  and public API regression;
- full pytest, Ruff, mypy, Web lint/typecheck/test/build, browser E2E,
  security/audit/package, `git diff --check`, and exact implementation
  allowlist; and
- independent read-only review with P0/P1/P2 classification, followed by
  hosted CI, CodeQL, merge, and post-merge verification only when P0/P1 = 0.

Executed results for the completed V7-08 implementation are summarized above
and in `ROADMAP_V7.md`.

## Acceptance criteria

The design was accepted when:

1. V7-08 has exactly one bounded responsibility: transient local human visual
   judgment to advisory readiness for one existing Page;
2. Project and Page come only from the route and all evidence identity is
   server-resolved;
3. the request accepts only bounded reviewer-authored fields and rejects all
   attempt, asset, provenance, QA, Provider, digest, path, URL, approval, and
   workflow authority;
4. the exact V7-07 image remains the visual subject and is independently
   revalidated before assessment;
5. the V7-06 evaluator remains canonical for readiness and its closed status
   precedence is unchanged;
6. `Generated` cannot become `ready`, `QualityChecked` may become advisory
   `ready`, and `Approved` is not reopened;
7. readiness, review input, and client result are not persisted and create or
   repair no state;
8. `ready` never approves, transitions, gates, fills, enables, or invokes the
   existing approval form or endpoint;
9. existing routes, DTOs, public Python API, StateMachine, WorkflowEngine,
   schemas, dependencies, CORS, Provider, I02, v5, and v6 remain unchanged;
10. the docs-only diff stays within the exact two-file allowlist; and
11. independent review, required CI, CodeQL, and post-merge checks reported no
    blocking issue for the completed V7-08 implementation (see evidence above).

## Authorization gate

At acceptance, RFC-V7-006 authorized only this docs-only design record and the
matching V7-08 roadmap update. The implementation was separately approved and
completed as PR #36 (see evidence above); that authorization is exhausted. This
RFC does not authorize follow-up implementation, asset access beyond existing
behavior, human-review persistence beyond the completed scope, quality
execution, approval, Page mutation, Provider calls, live generation, I02,
dependencies, `main`, versioning, release, tag, publication, Settings, branch
deletion, force push, or history rewriting.

Any future implementation requires a new exact allowlist, explicit
implementation authorization, applicable security and compatibility review,
and executed quality gates. If implementation requires an existing public DTO
change, public Python export, StateMachine state or command, persistence or
schema change, dependency, remote surface, durable review record, approval
coupling, or I02 authority, it is outside this RFC and must stop.
