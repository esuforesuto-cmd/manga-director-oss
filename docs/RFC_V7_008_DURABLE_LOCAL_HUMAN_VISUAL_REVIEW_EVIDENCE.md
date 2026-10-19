# RFC-V7-008: Durable Local Human Visual Review Evidence

- Status: Design approved; implementation and execution are not authorized
- Target line: v7.0 Discovery (Post-LTS)
- Roadmap item: V7-10 Durable Local Human Visual Review Evidence
- Delivery scope: docs-only design
- Decision owner: an explicit local human operator

## Decision boundary

This RFC freezes the smallest local-only persistence boundary that can record
one explicit V7-08 human visual judgment as immutable evidence for the exact
Page, generation attempt, output, provenance, Visual QA report, and safely
leased PNG that the server resolved during the request.

The future operation is separate from the existing transient V7-08 assessment.
It repeats the complete server-owned proof, keeps the V7-07 exact-file lease
through the evidence commit, and appends one canonical record to a dedicated
private LocalFile sidecar. It never trusts a browser-supplied review ID,
attempt, asset, provenance, digest, path, Provider, readiness result, or prior
client assessment.

The record is historical evidence only. `ready` remains advisory: recording
it does not approve a Page, change a Page state, run quality, invoke the
`StateMachine` or `WorkflowEngine`, alter the existing approval action, or
become a prerequisite for V7-09 download.

This RFC itself creates no route, database, directory, source code, test,
DTO, public Python export, dependency, migration, or runtime behavior. It
authorizes none.

## Problem

V7-06 defines deterministic human visual QA approval readiness. V7-07 proves
the exact Page-to-ledger-to-generation-evidence-to-owner-to-bytes chain. V7-08
accepts an explicit human judgment and returns a safe advisory result, but it
intentionally persists nothing. V7-09 downloads only an already approved PNG
and intentionally ignores V7-08 results.

Consequently, a completed V7-08 review disappears after navigation or process
restart. The system cannot later demonstrate which exact output was reviewed,
who supplied the judgment, which complete checklist was used, or whether the
result was `ready`, `needs_review`, or `blocked`. This conflicts with the
RFC-V7-004 requirement that earlier `blocked` and `needs_review` results remain
historical evidence rather than being overwritten.

Reusing `Page.review` would be incorrect: that field belongs to the earlier
canonical `Reviewed` workflow stage and is part of the existing Project
aggregate contract. Adding review evidence to `Page`, approval, workflow
history, the generation-evidence database, or the asset registry would mix
owners and require unrelated schema or compatibility changes.

A separate immutable evidence owner is therefore required before any later
approval-linking, review-history, or audit feature can be considered.

## Planning summary

- **Title:** V7-10 Durable Local Human Visual Review Evidence
- **Objective:** Persist one canonical, server-bound human visual review
  record without changing workflow, approval, or existing V7-08 behavior.
- **Scope:** One existing LocalFile Project, one existing `Generated` or
  `QualityChecked` Page, one complete human judgment, the existing V7-07 proof,
  the existing V7-08 evaluator, one private append-only sidecar, and one
  explicit local response.
- **Inputs:** Project ID and positive Page number from the route plus the same
  bounded reviewer-authored fields already accepted by V7-08.
- **Outputs:** One persisted or idempotently confirmed immutable evidence
  record and a redacted result, or one fail-closed response with no write.
- **Dependencies:** Completed V7-06, V7-07, V7-08, V7-09, the authoritative
  LocalFile Project, and the existing private durability root.
- **Estimated complexity:** Medium for a separately approved implementation;
  Low for this docs-only design.
- **Architecture notes:** One private Application write service composes a
  retained V7-08 proof with one dedicated SQLite owner. HTTP and Web remain
  adapters, and no Page or workflow persistence is touched.

## Goals

- Record a complete explicit human judgment against one exact verified image.
- Preserve every successful `ready`, `needs_review`, or human/QA-derived
  `blocked` assessment as immutable historical evidence.
- Keep the exact-file lease active until the evidence transaction commits or
  rolls back.
- Derive the record identity and every authoritative binding on the server.
- Make exact retries idempotent while rejecting conflicting or corrupt state.
- Keep all records outside the Project aggregate, workflow history, approval,
  generation-evidence store, and asset registry.
- Preserve the V7-08 transient endpoint and response behavior unchanged.
- Preserve approval as a separate explicit human workflow command.
- Fail closed without repair, migration, fallback, or partial evidence.

## Non-goals

- changing V7-06 evaluation rules, status precedence, criteria, or public
  meaning;
- changing V7-07 presentation, proof, exact-file validation, or lease safety;
- changing V7-08 request, response, route, transient semantics, or
  `analysisOnly` result;
- making review evidence mandatory for approval or V7-09 download;
- approving, rejecting, revoking, reopening, reapproving, or transitioning a
  Page;
- changing `Page.review`, `Page.approval`, Project JSON, workflow history,
  Repository protocols, LocalFile formats, `StateMachine`, or
  `WorkflowEngine`;
- review listing, browsing, search, pagination, deletion, update, recovery,
  export, synchronization, signing, attestation, or remote audit;
- accepting caller-selected review ID, Project or Page identity in the body,
  attempt, asset, provenance, QA reference, digest, path, storage name, root,
  URI, URL, Provider, prior assessment, readiness status, or approval data;
- automatic persistence on image load, Page load, refresh, navigation,
  transient V7-08 assessment, quality action, or approval;
- authentication, authorization, roles, identity verification, or treating
  `reviewerId` as a credential or approver identity;
- Provider construction or calls, generation, regeneration, retry, fallback,
  network lookup, DNS, proxy, redirect, or outbound request;
- CLI, MCP, SDK, Plugin, public Python, LAN, wildcard, cloud, or remote
  surfaces;
- I02 or use of I02 state, authority, contracts, persistence, or recovery;
- dependency, lockfile, package metadata, version, release, tag, publication,
  Settings, `main`, force-push, history-rewrite, or branch-deletion changes.

## Source contracts

The future feature composes existing owners without replacing them:

- the LocalFile Project remains authoritative for the exact Page, persisted
  state, logical generated-asset descriptor, and workflow history;
- the V7-07 private proof remains authoritative for the applied workflow
  ledger binding, exact generation evidence, provenance, owner registry,
  containment, file identity, size, SHA-256, strict PNG, and same-opened-bytes
  lease;
- the V7-08 Application service remains authoritative for server-owned Page
  resolution, Visual QA construction, human-judgment binding, and use of the
  V7-06 evaluator;
- the V7-06 report remains the canonical advisory readiness result and cannot
  approve or transition a Page;
- the existing approval action and `StateMachine` remain the sole authority
  for reaching `Approved`;
- the new evidence owner may persist only an already completed canonical
  V7-08 proof while its exact-file lease is retained; and
- HTTP and Web remain delivery adapters and acquire no evidence-selection,
  filesystem, workflow, approval, or Provider authority.

No individual Page field, caller assertion, prior client result, record row,
reviewer identity, or readiness status independently authorizes persistence.
Every required authority must agree during the same request.

## Frozen architecture

### Explicit local record operation

A separately approved implementation may add exactly one logical operation:

`POST /projects/{project_id}/pages/{page_number}/visual-review-evidence`

The operation is available only through the existing loopback workflow API
and exact local Web-origin policy. It does not replace or modify:

`POST /projects/{project_id}/pages/{page_number}/visual-review-readiness`

The path supplies the only Project and Page selectors. Query parameters are
rejected. The request body carries only an explicit human judgment.

Before integer conversion or repository access, the raw Page-number segment
must match `^[1-9][0-9]{0,9}$` and its numeric value must be no greater than
`2147483647`. This route-local bound does not change the Page model.

The recording route requires `application/json` and exactly one syntactically
valid `Origin` whose normalized origin exactly matches the existing local Web
allowlist. Missing, duplicate, malformed, `null`, remote, LAN, or mismatched
origins fail before repository, asset, or sidecar access. Existing CORS policy
is transport enforcement, not evidence or approval authority.

### Request contract

The body reuses the V7-08 human-input contract without adding authority:

- `reviewerId`: one bounded nonblank logical local reviewer reference;
- `reviewedAt`: one timezone-aware caller-supplied timestamp;
- `checklist`: exactly one decision for every V7-06 visual criterion;
- `overallJudgment`: `acceptable_for_approval_consideration`,
  `further_review_required`, or `blocked`; and
- `rationale`: bounded nonblank human-authored text.

Each checklist entry contains only its closed criterion, closed outcome, and
bounded rationale. Only `props` and `continuity_comparison` may be
`not_applicable`. Missing, duplicate, unknown, inconsistent, or extra fields
fail closed before evidence access.

The body must reject `projectId`, `pageNumber`, `pageId`, `reviewId`,
`attemptId`, `assetId`, `outputAssetId`, `provenanceReference`,
`qaReportReference`, `provider`, `digest`, `path`, `storageName`, `root`, `uri`,
`url`, `status`, `ready`, `findings`, `approvedBy`, workflow commands, prior
assessment results, and arbitrary metadata.

Reviewer-authored values are evidence, not credentials. Existing V7-08
bounds and unsafe-text rejection remain authoritative.

### Server-owned proof and commit flow

The complete future flow is:

~~~text
explicit local "Record review evidence" action
        |
        v
bounded loopback POST with human fields only
        |
        v
authoritative LocalFile Project -> exact persisted Page
        |
        v
existing V7-07 private proof
  -> applied workflow ledger binding
  -> exact generation evidence / attempt / output / provenance
  -> owner registry / contained ordinary file
  -> size + SHA-256 + strict PNG on the same opened bytes
        |
        v
existing V7-08 private assessment proof
  -> canonical Visual QA
  -> server-derived review ID and exact human-judgment binding
  -> canonical V7-06 readiness report
        |
        v
new private review-evidence owner while lease remains held
  -> append or exact idempotent confirmation
        |
        v
Application finalizes the persistence outcome
  -> release lease exactly once
  -> build the redacted response
~~~

The future V7-08 Application service may expose one additional private proof
capability so the existing `assess()` and the new writer share the same
resolution and evaluation logic. Existing `assess()` output and behavior must
remain unchanged. The private proof must carry the canonical report and its
retained release capability; it is not exported from the package.

The writer must not accept a precomputed report from HTTP or reconstruct a
partial result with `model_construct`, placeholders, `object()`, or unchecked
dictionaries. It persists only a fully validated report produced by the
existing services during the same request.

### Persistable record

One immutable record contains only canonical logical evidence:

- a fixed private schema identifier and version;
- the server-derived `review_id`;
- Project ID, Page ID, positive Page number, and persisted Page state;
- generation attempt ID, output asset ID, provenance reference, and canonical
  QA report reference;
- reviewer reference and caller-supplied timezone-aware review timestamp;
- the complete canonically ordered checklist, overall judgment, and rationale;
- canonical readiness status, matching `ready` boolean, ordered findings, and
  ordered missing-prerequisite codes; and
- a canonical payload digest plus a binding fingerprint covering the Page,
  attempt, output, provenance, QA reference, and review identity.

The record does not copy image bytes, paths, storage names, roots, registry
rows, Provider metadata, approval data, browser headers, current server time,
random values, or secrets. The payload must round-trip through closed frozen
models before insert and after lookup.

### Dedicated private persistence owner

The first implementation slice uses one dedicated private owner below the
existing trusted Next Generation normal-execution durability root, equivalent
to:

`_next_generation_normal_execution/review-evidence/human-visual-review-evidence.sqlite3`

This is a new private sidecar schema, not a Project or Repository schema
change. `LocalFileRepository` only supplies its existing fixed private root;
it does not gain fields, methods, migrations, or protocol changes.

The owner must:

- validate absolute fixed containment and reject symlink, junction, or reparse
  identities for its root and database;
- create its directory and version-1 schema only during the explicit record
  operation when no prior database or user tables exist;
- use SQLite transactions with full durability and one bounded lock timeout;
- validate the exact table, columns, primary keys, schema version, journal
  mode, canonical payload, payload digest, and binding fingerprint;
- treat an exact canonical retry as `confirmed`, without adding a second row;
- append every distinct valid review, including later reviews of the same
  output, under its distinct server-derived review ID;
- reject identity conflicts, duplicate ambiguous rows, corruption, unsupported
  schema, unsafe file identity, and transaction failure without repair;
- never update, delete, replace, merge, compact, migrate, vacuum, checkpoint,
  or choose a latest/best record; and
- commit or roll back its transaction and close every database connection on
  success, exact retry, conflict, and exception.

The sidecar owner never owns or releases the asset proof or exact-file lease
and cannot observe HTTP response lifetime. The private Application write
service owns the retained proof. After the owner has returned a committed,
confirmed, or failed outcome, the Application service releases the proof in
one `finally` boundary exactly once before it returns or raises to HTTP.

A private exact-ID lookup may exist only for idempotency, post-write
verification, focused tests, and future separately authorized composition.
There is no HTTP list, search, read, delete, update, export, or recovery route
in V7-10. Any standalone reader must open only an existing database with
`mode=ro` and query-only semantics and must create or repair nothing.

### Atomicity and lease lifetime

The exact V7-07 lease remains active from byte validation through the final
SQLite commit or rollback. The persisted record therefore describes the same
opened bytes that passed size, SHA-256, media-type, and strict-PNG validation.

The private Application write service, not the SQLite owner or HTTP adapter,
owns this lease lifetime. It releases the retained proof exactly once after
the persistence outcome is final and before the HTTP response object is
created. Therefore a later response abort has no live asset lease to release.

The operation has only two durable outcomes:

- one complete canonical row is committed or exactly confirmed; or
- no row is added and the request fails closed.

There is no state in which a success response is returned for an uncommitted
record, a partial record exists, or the file is reopened by path after proof.
An HTTP response abort after commit does not delete the evidence or trigger a
second lease release; an exact retry confirms the existing row.

### Page-state behavior

| Persisted Page state | Recording behavior |
| --- | --- |
| `Draft` through `PromptBuilt` | Fail closed; no generated review subject exists. |
| `Generated` | Persist a valid `needs_review` or human/QA-derived `blocked` result; it cannot become `ready`. |
| `QualityChecked` | Persist a valid `ready`, `needs_review`, or human/QA-derived `blocked` result. |
| `Approved` | Fail closed; V7-10 does not reopen review. Existing historical records remain unchanged. |

Infrastructure, proof, schema, corruption, input, or persistence failures are
not review judgments and must not be persisted as `blocked` evidence.

### Response and redaction contract

A successful response contains only:

- `status`: `ready`, `needs_review`, or `blocked`;
- the matching `ready` boolean;
- `pageState`: `Generated` or `QualityChecked`;
- deterministic ordered redacted findings;
- deterministic ordered missing-prerequisite codes;
- `evidenceRecorded: true`;
- `idempotentReplay`: the matching boolean; and
- `analysisOnly: true`.

`analysisOnly` continues to describe the readiness result: durable storage
does not turn readiness into approval authority.

The response excludes review ID, reviewer identity, reviewer rationale,
checklist text, attempt ID, asset ID, provenance, QA reference, Provider,
digest, path, storage name, root, database, SQL, approval, workflow command,
and next state.

Malformed input or request admission returns the existing generic validation
class. Missing, unsafe, stale, ambiguous, or mismatched authoritative evidence
returns the generic not-found class. Store conflict, corruption, or unavailable
durability returns one generic redacted persistence-unavailable class. These
responses reveal no existence, row count, identity, filesystem, SQL, or
Provider detail.

All responses use `Cache-Control: no-store` and
`X-Content-Type-Options: nosniff`; they emit no ETag, Last-Modified, Location,
redirect, filename, or cache validator.

### Explicit Web behavior

The existing V7-08 form may add a separate explicit `Record review evidence`
control while retaining `Assess readiness` as its transient operation.

- Page load, image load, refresh, navigation, polling, transient assessment,
  quality, and approval never record evidence.
- The recording action sends the current complete human fields to the new
  fixed Project-and-Page route; it sends no prior result or internal identity.
- The server always recomputes the authoritative proof and readiness result.
- The UI labels successful storage as historical evidence, not approval.
- A successful record does not fill, enable, hide, invoke, replace, or gate
  the approval form.
- `reviewerId` is never copied into `approvedBy`.
- Browser local storage, IndexedDB, cookies, and background queues are not
  added.

The existing Page view and visibility predicates already bound the form to
the applicable generated-image states; no new workflow-view or Page-view
authority is required.

### Approval and workflow separation

V7-10 does not alter approval eligibility. In particular:

- a persisted `ready` record is neither approval nor authorization;
- an existing `blocked` record does not transition, reject, revoke, or lock a
  Page;
- multiple records do not select a winner, latest judgment, consensus, or
  approver;
- the approval endpoint neither reads nor writes the new sidecar;
- V7-09 neither reads nor requires the new sidecar; and
- no `StateMachine` state, command, transition, event, or WorkflowEngine step
  is added or changed.

Any future approval-to-review linkage requires a separate RFC, an explicit
policy for selecting immutable records, and separate implementation approval.

### Network, security, and privacy

- Loopback binding and the exact existing local Web-origin allowlist remain
  unchanged.
- The new route accepts only JSON from the allowed local Web origin and is not
  advertised as a general local automation API.
- No DNS, proxy, redirect following, HTTP client, Provider, remote URL, or
  outbound request is permitted.
- Request size, criterion count, rationale length, finding count, and stored
  payload size are bounded.
- Reviewer text is data only and never becomes SQL, HTML, a path, log format,
  filename, approval identity, or authorization input.
- Parameterized SQL is mandatory; raw reviewer text is never interpolated.
- The feature adds no access log, analytics, notification, telemetry, secret,
  or browser persistence.
- Errors, repr output, and responses redact human text and internal binding or
  storage data.

## Determinism and idempotency

The existing server-derived review ID remains the identity of one canonical
submission bound to one exact output. It is calculated without current time,
randomness, filesystem order, locale, environment, network, or Provider
results.

For identical authoritative state and identical canonical human input:

- the V7-08 proof and readiness report are identical;
- the review ID, payload, payload digest, and binding fingerprint are
  identical;
- the first valid operation appends one row;
- every exact retry confirms that row and reports `idempotentReplay: true`;
  and
- no retry modifies timestamps, order, counters, Page state, or evidence.

A different valid human judgment produces a distinct review ID and an
additional immutable row. No record supersedes or overwrites another.

## Failure and recovery semantics

Failure is fail-closed and transactionally bounded.

- invalid request or origin evidence is rejected before authoritative access;
- unavailable Page, ledger, generation evidence, asset owner, safe lease, or
  canonical assessment produces no review row;
- unsupported platform, unsafe filesystem identity, oversize, digest mismatch,
  malformed PNG, trailing data, or partial read produces no review row;
- database identity, schema, canonicalization, digest, binding, duplicate,
  conflict, lock, commit, or I/O failure produces no success response and no
  repair;
- no failure chooses another attempt, output, record, Provider, file, or
  fallback; and
- no failure retries automatically, regenerates, runs quality, approves,
  transitions, notifies, or invokes I02.

Recovery consists only of correcting authoritative state through a separately
authorized existing workflow and making another explicit record request.
Corrupt or unsupported sidecars require a separately authorized recovery or
migration design; V7-10 does not repair them.

## Public contract compatibility

A separately approved implementation may add one loopback-only POST, one
closed request/response pair, one private Application capability, one private
production evidence owner, and one explicit Web control. Existing routes and
JSON DTOs remain unchanged.

Public Python imports and exports remain unchanged. The private modules use
`__all__ = ()` and do not alter package export files. CLI, MCP, SDK, Plugin,
Repository protocols, Project and Page models, LocalFile serialization,
Provider contracts, generation, quality, approval, `StateMachine`,
`WorkflowEngine`, V7-06 through V7-09, v5, and v6 behavior remain compatible.

The new private sidecar has its own version-1 schema and requires no migration
of existing Project, repository, ledger, generation-evidence, asset-registry,
or approval data. Its directory and database are absent until the first
successful explicitly requested write.

Any need to change an existing DTO, public Python export, Page or Repository
schema, LocalFile contract, StateMachine, WorkflowEngine, approval behavior,
V7-09 eligibility, dependency, remote surface, Provider, or I02 authority is a
scope expansion and must stop.

## Candidate implementation allowlist

This design identifies the following smallest candidate set for a future
implementation. It is planning evidence only and is not implementation
authorization:

1. `src/manga_director/production/next_generation_durable_human_visual_review_evidence.py` (new)
2. `src/manga_director/application/human_visual_review_evidence.py` (new)
3. `src/manga_director/application/human_visual_review_readiness.py`
4. `src/manga_director/api/composition.py`
5. `src/manga_director/api/workflow.py`
6. `tests/test_next_generation_durable_human_visual_review_evidence.py` (new)
7. `tests/test_safe_local_human_visual_review_evidence.py` (new)
8. `web/lib/api/types.ts`
9. `web/lib/api/client.ts`
10. `web/components/human-visual-review-form.tsx`
11. `web/tests/api-client.test.ts`
12. `web/tests/ui-contract.test.ts`
13. `web/e2e/mock-api.mjs`
14. `web/e2e/workflow.spec.ts`
15. `docs/ROADMAP_V7.md`

`web/components/page-workflow.tsx` and `web/lib/workflow-view.ts` are excluded
because the existing V7-08 form placement and visibility rules are sufficient.
`LocalFileRepository`, Project models, existing persistence owners, package
exports, StateMachine, WorkflowEngine, approval, and V7-09 files are also
excluded.

The candidate must be rechecked and explicitly approved as an exact allowlist
before implementation. A sixteenth file is a scope expansion.

## Validation plan

This docs-only design requires:

- exact two-file allowlist:
  `docs/RFC_V7_008_DURABLE_LOCAL_HUMAN_VISUAL_REVIEW_EVIDENCE.md` and
  `docs/ROADMAP_V7.md`;
- local Markdown-link resolution and `git diff --check`;
- zero source, test, dependency, lockfile, workflow, package-metadata, version,
  Settings, or `main` diff;
- architecture, persistence-owner, exact-file lease, privacy,
  approval-boundary, public-contract, and compatibility review;
- independent read-only review with P0 = 0 and P1 = 0 before merge; and
- required hosted CI, CodeQL, and post-merge verification.

A separately approved implementation would additionally require:

- focused positive cases for `Generated` historical `needs_review` and
  `QualityChecked` `ready`, `needs_review`, and human/QA-derived `blocked`;
- exact Page-to-ledger-to-generation-evidence-to-owner-to-same-opened-bytes-to-
  judgment-to-record correlation;
- proof that the exact-file lease remains active through commit or rollback;
- proof that the Application writer alone releases the retained proof exactly
  once after the persistence outcome and before HTTP response construction;
- first insert, process-restart lookup, exact idempotent retry, distinct-review
  append, conflict, duplicate, lock, rollback, commit-failure, and concurrent
  writer cases;
- rejection of earlier and `Approved` states, query parameters, wrong content
  type, missing or mismatched origin, extra fields, body selectors, prior
  results, paths, URLs, secrets, incomplete checklist, duplicate criteria, and
  invalid `not_applicable` use;
- missing, ambiguous, stale, corrupt, mismatched, unsafe-file, symlink,
  junction, reparse, oversize, digest, strict-PNG, trailing-data, partial-read,
  schema, canonical-payload, payload-digest, and binding-fingerprint rejection;
- proof that invalid or infrastructure failures create no row and that
  existing invalid sidecars are never repaired or migrated;
- before/after equivalence for Project, Page, workflow history, `review`,
  `approval`, ledger, generation evidence, registry, asset, and all unrelated
  service state;
- proof that the transient V7-08 endpoint, Page/image load, refresh, quality,
  approval, and V7-09 download create no review record;
- exact response/header/redaction checks with no human text, internal identity,
  Provider, digest, path, storage, SQL, redirect, or cache-validator leak;
- unchanged CORS allowlist, loopback binding, and no DNS, proxy, Provider, or
  outbound request;
- no approval, StateMachine, WorkflowEngine, Page mutation, generation, retry,
  fallback, review selection, deletion, recovery, or I02 regression;
- V7-06, V7-07, V7-08, V7-09, approval, HTTP, Web, LocalFile, generation,
  quality, v5/v6, and public API compatibility regression;
- full pytest, Ruff, mypy, Web lint/typecheck/test/build, browser E2E,
  security/audit/package, `git diff --check`, and exact implementation
  allowlist; and
- independent read-only review with P0/P1/P2 classification, followed by
  hosted CI, CodeQL, merge, and post-merge verification only when P0/P1 = 0.

Those implementation checks are planning only and are not executed by this
RFC.

## Acceptance criteria

The design is accepted when:

1. V7-10 has one responsibility: explicit immutable local human visual review
   evidence for one exact existing Page output;
2. the existing V7-08 assessment remains transient and behaviorally unchanged;
3. Project and Page come only from the route, while every generation, asset,
   QA, readiness, and review identity is resolved or derived by the server;
4. persistence occurs only after the full V7-07/V7-08 proof and while the
   same-opened-bytes lease is retained;
5. valid `ready`, `needs_review`, and human/QA-derived `blocked` reports are
   immutable historical records, while infrastructure failures are not;
6. exact retries are idempotent, distinct reviews append, and no record can be
   updated, deleted, replaced, selected as latest, or used as approval;
7. the private sidecar is isolated from Project, Page, workflow, approval,
   generation-evidence, registry, and Repository schemas;
8. no load, refresh, assessment, quality action, approval, or download records
   evidence automatically;
9. approval, StateMachine, WorkflowEngine, V7-09, existing DTOs, public Python
   API, CLI, MCP, SDK, Plugin, Provider, dependencies, I02, v5, and v6 remain
   unchanged;
10. the docs-only diff stays within the exact two-file allowlist; and
11. independent review, required CI, CodeQL, and post-merge checks report no
   blocking issue.

## STOP conditions

Design or future implementation must stop on any of the following:

- a third docs file or a sixteenth implementation file is required;
- an existing JSON DTO, public Python export, Page, Project, Repository,
  LocalFile, ledger, generation-evidence, registry, approval, or workflow
  schema must change;
- `Page.review` or `Page.approval` must store or select V7-10 evidence;
- approval, StateMachine, WorkflowEngine, V7-09 eligibility, Provider,
  generation, I02, dependency, lockfile, CORS, remote surface, `main`, version,
  release, tag, Settings, branch deletion, force push, or history rewrite is
  required;
- exact-file lease safety cannot be held through evidence commit;
- an existing invalid sidecar would need repair or migration;
- a P0/P1 cannot be resolved within the separately approved allowlist; or
- required local or hosted validation, CI, CodeQL, conflict, or scope checks
  fail.

## Authorization gate

Approval of RFC-V7-008 authorizes only this docs-only design record and the
matching V7-10 roadmap entry. It does not authorize implementation, HTTP or
Web changes, sidecar creation, database or directory creation, human-review
persistence, asset access beyond existing behavior, Page mutation, quality,
approval, workflow transitions, Provider calls, generation, I02, dependencies,
`main`, versioning, release, tag, publication, Settings, branch deletion,
force push, or history rewriting.

Any future implementation requires explicit approval of a revalidated exact
allowlist, the new private sidecar schema, the additive loopback POST, and the
applicable validation plan. Documentation acceptance alone grants no runtime
or persistence authority.
