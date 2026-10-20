# RFC-V7-009: Safe Local Human Visual Review Evidence History

- Status: Design approved; implementation and execution are not authorized
- Target line: v7.0 Discovery (Post-LTS)
- Roadmap item: V7-11 Safe Local Human Visual Review Evidence History
- Delivery scope: docs-only design
- Decision owner: an explicit local human operator

## Decision boundary

This RFC freezes the smallest loopback-only, read-only boundary that lets a
local human inspect the immutable V7-10 human visual review evidence history
for one authoritative Page.

The future reader reuses the existing V7-10 private sidecar and its exact
schema, canonical payload, digest, and binding validation. It opens only an
existing database with SQLite read-only and query-only semantics. It creates,
updates, deletes, repairs, compacts, checkpoints, vacuums, or migrates
nothing.

Every matching review remains historical evidence. The reader does not choose
a latest, newest, best, winning, consensus, or approval-relevant review.
`ready` remains advisory and never becomes approval, authorization, a Page
transition, or V7-09 download eligibility.

This RFC itself creates no route, reader, DTO, Web component, database,
directory, source code, test, dependency, migration, or runtime behavior. It
authorizes none.

## Problem

V7-10 durably records one complete human visual judgment against the exact
Page, generation attempt, output, provenance, Visual QA report, and safely
leased PNG resolved during the explicit record request. It preserves distinct
reviews as immutable rows and provides only a private exact-ID lookup for
idempotency, post-write verification, and focused tests.

After navigation or process restart, the local Web application cannot inspect
those records. A human would have to open the private SQLite sidecar directly,
which bypasses the Application ownership boundary, canonical validation,
redaction policy, exact Page binding, and safe local HTTP/Web conventions.

The store is append-only and may contain multiple judgments for the same Page.
Selecting one record by timestamp, status, insertion order, or perceived
quality would silently introduce policy that V7-10 explicitly deferred.

A separate read-only composition is therefore required. It must show bounded
Page history without changing the V7-10 store, treating a record as approval,
or creating another workflow authority.

## Planning summary

- **Title:** V7-11 Safe Local Human Visual Review Evidence History
- **Objective:** Display immutable V7-10 evidence for one authoritative Page
  through an explicit loopback-only Web action without mutating or selecting
  any record.
- **Scope:** One existing LocalFile Project, one existing Page, the existing
  V7-10 sidecar, one private read-only Application service, one additive GET,
  and one explicit Web history panel.
- **Inputs:** Project ID and positive Page number from the route only.
- **Outputs:** One complete bounded Page-history response in canonical identity
  order, an empty complete history, or one redacted fail-closed response.
- **Dependencies:** Completed V7-08, V7-09, and V7-10; the authoritative
  LocalFile Project; and the existing V7-10 private sidecar contract.
- **Estimated complexity:** Medium for a separately approved implementation;
  Low for this docs-only design.
- **Architecture notes:** The production owner reads and validates its own
  sidecar, an Application service binds the result to the authoritative Page,
  and HTTP/Web remain presentation adapters.

## Goals

- Let a local human explicitly inspect all bounded V7-10 records for one Page.
- Reuse the existing V7-10 sidecar, schema version, payload models, digests,
  fingerprints, filesystem containment, and corruption checks.
- Preserve every successful `ready`, `needs_review`, and `blocked` record as
  equal historical evidence.
- Bind the history request to the authoritative Project, Page number, and Page
  ID before returning evidence.
- Keep all reads deterministic, bounded, redacted, and fail-closed.
- Return no partial history when integrity or response bounds cannot be
  satisfied.
- Keep history access separate from assessment, recording, quality, approval,
  workflow execution, generation, and download.
- Preserve existing public and compatibility contracts.

## Non-goals

- appending, updating, deleting, replacing, merging, repairing, compacting,
  vacuuming, checkpointing, or migrating review evidence;
- selecting or recommending a latest, newest, best, winning, consensus, most
  acceptable, or approval-relevant review;
- ordering or filtering by reviewer, caller-supplied `reviewedAt`, status,
  judgment, Page state, quality, or approval;
- making evidence mandatory for approval or V7-09 download;
- treating `ready` as approval, authorization, acceptance, or a workflow
  command;
- approving, rejecting, revoking, reopening, reapproving, or transitioning a
  Page;
- changing V7-08 assessment or V7-10 recording behavior;
- changing `Page.review`, `Page.approval`, Project JSON, workflow history,
  Repository protocols, LocalFile formats, `StateMachine`, or
  `WorkflowEngine`;
- changing the V7-10 schema, tables, columns, indexes, journal mode, payload,
  digest, binding fingerprint, record identity, or append semantics;
- arbitrary search, caller-selected sort, caller-selected limit, export,
  synchronization, signing, attestation, remote audit, or general reporting;
- accepting caller-selected review, output, attempt, provenance, QA, Provider,
  digest, path, storage, root, URI, URL, approval, or workflow authority;
- automatic loading on Page load, refresh, navigation, polling, assessment,
  record, quality, approval, or download;
- authentication, authorization, identity verification, roles, or treating a
  reviewer reference as a credential or approver identity;
- Provider construction or calls, generation, regeneration, retry, fallback,
  network lookup, DNS, proxy, redirect, or outbound request;
- CLI, MCP, SDK, Plugin, public Python, LAN, wildcard, cloud, or remote
  surfaces;
- I02 or use of I02 state, authority, contracts, persistence, or recovery;
- dependency, lockfile, package metadata, version, release, tag, publication,
  Settings, `main`, force-push, history-rewrite, or branch-deletion changes.

## Source contracts

The future feature composes existing owners without replacing them:

- the authoritative LocalFile Project supplies the exact Project, Page number,
  Page ID, and current persisted Page state;
- the V7-10 private owner remains the only component that knows the sidecar
  root, database, schema, SQL, canonical payload, digest, and binding details;
- the V7-10 immutable payload remains the source for the stored human judgment
  and advisory result;
- the private Application reader binds owner results to the authoritative Page
  and creates the redacted transport-neutral history result;
- HTTP validates the fixed local request and maps only the closed history DTO;
- Web initiates the read explicitly and renders the response as text; and
- the existing approval action and `StateMachine` remain the sole authority
  for reaching `Approved`.

No record, status, reviewer, timestamp, output identifier, or Web display
independently authorizes approval, workflow action, or download.

## Frozen architecture

### Explicit local history operation

A separately approved implementation may add exactly one logical read:

`GET /projects/{project_id}/pages/{page_number}/visual-review-evidence`

The existing V7-10 operation on the same resource remains unchanged:

`POST /projects/{project_id}/pages/{page_number}/visual-review-evidence`

The GET is available only through the existing loopback workflow API and a
new explicit local Web control. It is not exposed on a Provider, remote, LAN,
wildcard, CLI, MCP, SDK, Plugin, or public Python surface.

The route supplies the only Project and Page selectors. Request bodies are
forbidden. Query parameters are forbidden; the first slice has no filter,
sort, cursor, offset, or caller-selected limit.

Before integer conversion or repository access, the raw Page-number segment
must match `^[1-9][0-9]{0,9}$` and its numeric value must be no greater than
`2147483647`. This route-local bound does not change the Page model.

### Browser-read admission

Before Project or sidecar access, the route requires:

- exactly one syntactically valid `Origin` matching the existing local Web
  allowlist;
- exactly one syntactically valid `Referer` whose parsed origin matches the
  same allowlist;
- `Sec-Fetch-Mode: cors`;
- `Sec-Fetch-Dest: empty`; and
- an explicit JSON `Accept` value.

The route rejects a body, non-zero `Content-Length`, transfer encoding, query
parameters, duplicate admission headers, `Range`, `If-Range`, `If-Match`,
`If-None-Match`, `If-Modified-Since`, and `If-Unmodified-Since`.

These headers are browser admission evidence only. They are not persisted,
returned, logged by this feature, or treated as authentication. CORS remains
transport policy rather than review, Page, or approval authority.

### Authoritative Page binding

The Application reader loads exactly one authoritative Page from the route.
The first slice permits history inspection only while the current persisted
Page state is `Generated`, `QualityChecked`, or `Approved`.

The reader uses the authoritative Project ID, Page ID, and Page number as one
closed binding. A record must match all three stored values. A record for
another Page, another Project, or a conflicting Page identity is never
returned.

The reader does not require the current image file, V7-07 lease, generation
evidence, asset registry, approval artifact, or V7-09 proof. V7-10 already
bound and validated those facts at append time. Re-running them would make
historical evidence availability depend on current delivery state and would
expand the read into unrelated owners.

### Existing-store read discipline

The V7-10 owner may add one private Page-history read capability. It must:

- treat a completely absent review-evidence directory and database as an
  empty history without creating them;
- reject a present directory with a missing database as conflicting state;
- validate the fixed absolute root, directory, database identity, containment,
  and symlink, junction, or reparse exclusions before opening SQLite;
- reject WAL or unsupported database headers before SQLite can create or
  checkpoint support files;
- open only an existing database with `mode=ro`, `timeout=0.0`, and
  `isolation_level=None`;
- set and verify `PRAGMA query_only=ON`;
- apply one server-owned bounded SQLite read-work budget across schema
  validation, complete row validation, and the Page query;
- begin one read transaction, validate the exact V7-10 version-1 schema and
  every stored row, read matching records, roll back, and close;
- use parameterized SQL and closed internal payload models;
- return records in ascending `review_id` order solely as a deterministic
  canonical identity order; and
- create, update, delete, replace, normalize, repair, compact, migrate,
  vacuum, checkpoint, or clean up nothing.

An unavailable lock or exhausted read-work budget fails immediately. The
budget is an execution bound only; it never selects, skips, or returns a
subset of records. There is no automatic retry, alternate connection mode,
mutable fallback, copied database, temporary database, or partial result.

### Complete bounded history

The first slice returns at most 32 records for one Page and at most 1,048,576
UTF-8 bytes of serialized JSON.

Both limits are server-owned constants. The caller cannot change them. The
reader validates the complete matching set before returning success. If the
Page has more than 32 matching records, or the complete response would exceed
the byte limit, the request fails as unavailable. It does not truncate,
select, rank, summarize, or return only the first or last records.

Pagination or another bounded complete-history design requires a separate RFC.
It must not be inferred from this first slice.

### Response contract

A successful response contains only:

- `pageNumber`: the validated route Page number;
- `recordCount`: the exact number of returned records;
- `complete: true`;
- `readOnly: true`;
- `analysisOnly: true`; and
- `records`: the canonically ordered complete bounded history.

Each record contains only:

- `reviewId`;
- `outputAssetId`;
- `reviewerId`;
- `reviewedAt`;
- `pageState`: the stored `Generated` or `QualityChecked` state at recording;
- the complete canonically ordered checklist;
- `overallJudgment` and the overall rationale;
- `status`: `ready`, `needs_review`, or `blocked`;
- the matching `ready` boolean;
- deterministic ordered findings;
- deterministic ordered missing-prerequisite codes; and
- `analysisOnly: true`.

The top-level response does not assert the current Page state or approval. A
record's stored `pageState`, status, and `ready` value are historical evidence
only.

The response excludes Project ID, Page ID, attempt ID, provenance reference,
QA reference, binding fingerprint, payload digest, Provider, image bytes,
path, storage name, root, database, SQL, browser headers, approval identity,
workflow command, next state, and download eligibility.

All success and failure responses use `Cache-Control: no-store` and
`X-Content-Type-Options: nosniff`. They emit no ETag, Last-Modified, Location,
Content-Location, redirect, filename, or cache validator.

### Explicit Web behavior

The local Page view may show a separate `Human visual review evidence history`
panel for `Generated`, `QualityChecked`, and `Approved` Pages. The server
remains authoritative even when the UI hides the panel.

- Initial Page load, image load, refresh, navigation, and polling do not fetch
  history.
- One explicit `Show review evidence history` control starts one GET.
- A repeated explicit control may perform another complete read; it does not
  create or refresh evidence.
- Every record is displayed without selection, filtering, ranking, or a
  latest/best badge.
- The UI labels every status, including `ready`, as historical advisory
  evidence and not approval.
- The checklist may be collapsed for presentation, but no item is omitted
  from the received or rendered record.
- History state is not shared with the assessment, recording, quality,
  approval, or download controls.
- `reviewerId` is never copied into `approvedBy`.
- Browser local storage, IndexedDB, cookies, service-worker cache, background
  queues, and polling are not added.

Reviewer-authored text is rendered as text through the existing React
escaping behavior. It is never interpreted as HTML, Markdown, a path, a URL,
a command, or an authorization input.

## State behavior

| Current authoritative Page state | History behavior |
| --- | --- |
| `Draft` through `PromptBuilt` | Fail closed; the Page has not reached the evidence-history boundary. |
| `Generated` | Return the complete bounded matching history or an empty history. |
| `QualityChecked` | Return the complete bounded matching history or an empty history. |
| `Approved` | Return the unchanged historical records; do not reopen review or approval. |

The stored record `pageState` remains the state at evidence creation. V7-11
does not rewrite it to the current Page state.

## No mutation or selection

Success, empty history, repeated reads, response aborts, and every failure must
leave the following unchanged:

- Project and Page files and metadata;
- Page state, workflow history, artifacts, review, quality, continuity, and
  approval fields;
- V7-10 directory, database bytes, schema, rows, journals, and file metadata
  under application control;
- workflow ledger, generation evidence, asset registry, and generated asset;
- V7-08 transient results and V7-09 download eligibility; and
- all unrelated service state.

The operation does not compute a preferred record. Ascending `review_id` is a
stable technical presentation order only. It carries no recency, chronology,
quality, trust, approval, or supersession meaning. Caller-supplied
`reviewedAt` is displayed but never compared to select or rank records.

## Security

- Server binding remains loopback-only and the exact local CORS allowlist is
  unchanged.
- Browser admission is validated before Project or sidecar access.
- Request and response cardinality and byte size are bounded.
- SQLite validation and query work is bounded and budget exhaustion fails the
  whole request without a partial response.
- Only the production owner handles SQLite, roots, paths, schema, SQL, digest,
  and binding validation.
- Parameterized SQL is mandatory.
- A corrupt record anywhere in the validated store prevents a partial success.
- Missing, unsafe, duplicate, ambiguous, stale, conflicting, unsupported, or
  busy storage fails closed without repair.
- No DNS, proxy, redirect following, HTTP client, Provider, remote URL, or
  outbound request is permitted.
- No error contains reviewer text, rationale, checklist text, internal
  identity, Provider, digest, path, storage name, root, database, SQL,
  traceback, or exception detail.
- The feature adds no access log, analytics, telemetry, notification, secret,
  or credential handling.

## Privacy

History intentionally contains reviewer references, review timestamps,
checklist rationales, and overall rationale. Therefore:

- history is fetched only after an explicit local human action;
- JSON responses are non-cacheable and Web state remains process-local;
- no reviewer-authored value enters a URL, filename, header, log, HTML, SQL,
  browser durable storage, approval field, or authorization decision;
- the UI does not expose internal generation, filesystem, database, Provider,
  digest, or approval details; and
- a reviewer reference remains self-asserted evidence, not verified identity.

This feature is a local evidence viewer, not an authentication, authorization,
audit-publication, or identity-governance system.

## Determinism

For the same authoritative Page and unchanged V7-10 database, the returned
records, record count, field values, and ordering are identical.

- ordering uses canonical `review_id` ascending order only;
- no current time, filesystem enumeration, locale, random value, environment
  value, browser state, network result, Provider result, Page approval, or
  caller preference affects the result;
- an absent store deterministically produces an empty complete history; and
- repeated reads accumulate no state.

## Failure and recovery semantics

History inspection is fail-closed and read-only.

- malformed path or browser admission returns generic `422 invalid_input`
  before authoritative access;
- a missing Project or Page, or an ineligible current Page state, returns the
  generic `404 not_found` class;
- a valid Page with no review-evidence directory and database returns `200`
  with an empty complete history and creates nothing;
- a valid Page with an existing valid store but no matching records returns
  the same empty complete history;
- a present directory with a missing database, unsafe identity, WAL,
  unsupported schema, corruption, duplicate, binding mismatch, digest
  mismatch, ambiguous Page identity, lock, exhausted read-work budget, I/O
  failure, or exceeded history bound returns generic
  `503 history_unavailable`;
- no failure returns a validated subset from a store that failed complete
  validation; and
- no failure retries, falls back, repairs, cleans up, migrates, selects a
  record, runs quality, approves, transitions, downloads, regenerates,
  notifies, or invokes I02.

Recovery consists only of correcting authoritative state through a separately
authorized existing workflow or a future separately approved recovery design.
V7-11 adds no repair, migration, recovery, or retry command.

## Public contract compatibility

A separately approved implementation may add one loopback-only JSON GET, one
closed response family, one private Application reader, one private V7-10
owner read capability, and one explicit Web history panel.

The existing V7-10 POST route, request, response, append, idempotency, and
sidecar behavior remain unchanged. Existing HTTP DTOs are not modified. The
history DTOs are additive and closed.

Public Python imports and exports remain unchanged. New private modules use
`__all__ = ()` and package export files remain unchanged. CLI, MCP, SDK,
Plugin, Repository protocols, Project and Page models, LocalFile
serialization, Provider contracts, generation, quality, approval,
`StateMachine`, `WorkflowEngine`, V7-08, V7-09, V7-10, v5, and v6 behavior
remain compatible.

The V7-10 schema version remains 1. No migration, index, column, table, meta
row, directory, or alternate store is added. Any need to change one of those
contracts is a scope expansion and must stop.

## Candidate implementation allowlist

This design identifies the following smallest candidate set for a future
implementation. It is planning evidence only and is not implementation
authorization:

1. `src/manga_director/production/next_generation_durable_human_visual_review_evidence.py`
2. `src/manga_director/application/human_visual_review_evidence_history.py` (new)
3. `src/manga_director/api/composition.py`
4. `src/manga_director/api/workflow.py`
5. `tests/test_next_generation_durable_human_visual_review_evidence.py`
6. `tests/test_safe_local_human_visual_review_evidence_history.py` (new)
7. `web/lib/api/types.ts`
8. `web/lib/api/client.ts`
9. `web/components/human-visual-review-evidence-history.tsx` (new)
10. `web/components/page-workflow.tsx`
11. `web/lib/workflow-view.ts`
12. `web/tests/api-client.test.ts`
13. `web/tests/ui-contract.test.ts`
14. `web/e2e/mock-api.mjs`
15. `web/e2e/workflow.spec.ts`

`LocalFileRepository`, Project and Page models, existing public packages,
StateMachine, WorkflowEngine, approval, V7-09, Provider, generation,
dependency, and lock files are excluded.

The candidate must be rechecked and explicitly approved as an exact allowlist
before implementation. A sixteenth file is a scope expansion.

## Validation plan

This docs-only design requires:

- exact two-file allowlist:
  `docs/RFC_V7_009_SAFE_LOCAL_HUMAN_VISUAL_REVIEW_EVIDENCE_HISTORY.md` and
  `docs/ROADMAP_V7.md`;
- local Markdown-link resolution and `git diff --check`;
- zero source, test, dependency, lockfile, workflow, package-metadata, version,
  Settings, or `main` diff;
- architecture, store ownership, read-only SQLite, privacy, approval
  separation, public-contract, and compatibility review;
- independent read-only review with P0 = 0 and P1 = 0 before merge; and
- required hosted CI, CodeQL, and post-merge verification.

A separately approved implementation would additionally require:

- positive reads for one and multiple V7-10 records after process restart;
- exact authoritative Project ID, Page ID, and Page-number correlation;
- `Generated`, `QualityChecked`, and `Approved` Page-history cases;
- canonical `review_id` ordering without timestamp, status, quality, or
  approval selection;
- absent store and no-matching-record empty histories with equivalent
  before/after filesystem manifests;
- rejection of earlier Page states, query parameters, request bodies,
  transfer encoding, invalid raw Page numbers, missing or duplicate admission
  headers, conditional headers, and range requests;
- missing database under a present directory, symlink, junction, reparse,
  WAL, schema, canonical payload, digest, binding, duplicate, lock, I/O, and
  ambiguous Page identity failures;
- bounded SQLite read-work exhaustion without retry or partial history;
- proof that one invalid row prevents partial history and causes no repair;
- exact 32-record and 1,048,576-byte boundary tests with no truncation;
- exact closed response fields, empty response, header, and redaction tests;
- proof that Page load, image load, refresh, navigation, polling, V7-08
  assessment, V7-10 recording, quality, approval, and V7-09 download do not
  fetch history automatically;
- proof that `ready` does not fill, enable, gate, invoke, replace, revoke, or
  deny approval and does not change V7-09 eligibility;
- proof of no Project, Page, sidecar, ledger, evidence, registry, asset,
  workflow, review, approval, browser storage, Provider, generation, retry,
  fallback, network, or I02 mutation or call;
- V7-06 through V7-10, HTTP, Web, LocalFile, generation, quality, approval,
  v5/v6, and public API compatibility regression;
- full pytest, Ruff, mypy, Web lint/typecheck/test/build, browser E2E,
  security/audit/package, `git diff --check`, and exact implementation
  allowlist; and
- independent read-only review with P0/P1/P2 classification, followed by
  hosted CI, CodeQL, merge, and post-merge verification only when P0/P1 = 0.

Those implementation checks are planning only and are not executed by this
RFC.

## Acceptance criteria

The design is accepted when:

1. one explicit local GET returns only immutable V7-10 records for one exact
   authoritative Page;
2. the existing V7-10 sidecar, schema version, rows, payloads, digests,
   bindings, and append behavior remain unchanged;
3. a completely absent store is an empty complete history and creates no
   directory or database;
4. every existing store read uses read-only/query-only SQLite semantics and
   cannot repair, migrate, checkpoint, compact, vacuum, update, or delete;
5. all matching records are returned in canonical identity order within the
   fixed complete-history bounds, with no truncation or latest/best selection;
6. one corrupt or ambiguous store condition prevents partial disclosure;
7. history remains visible for an `Approved` Page without reopening review or
   approval;
8. reviewer text is exposed only through an explicit non-cacheable local Web
   read and is never persisted by the browser or reused as authority;
9. `ready` remains advisory and cannot affect approval, Page state,
   StateMachine, WorkflowEngine, or V7-09 eligibility;
10. no Provider, generation, network, I02, dependency, public API, Project,
    Page, or existing DTO change is introduced;
11. the docs-only diff stays within the exact two-file allowlist; and
12. independent review and required checks report no P0/P1 issue.

## STOP conditions

Design or future implementation must stop on any of the following:

- a third docs file or a sixteenth implementation file is required;
- the V7-10 schema, table, column, index, journal mode, payload, digest,
  fingerprint, row, or directory contract must change;
- update, delete, replace, repair, compact, vacuum, checkpoint, migration, or
  alternate persistence is required;
- partial history, automatic latest/best selection, or approval linkage is
  required;
- an existing JSON DTO, public Python export, Project, Page, Repository,
  LocalFile, approval, or workflow schema must change;
- `Page.review` or `Page.approval` must store or select V7-10 evidence;
- StateMachine, WorkflowEngine, V7-09 eligibility, Provider, generation, I02,
  dependency, lockfile, CORS, or remote surface must change;
- `main`, version, release, tag, Settings, publication, branch deletion,
  force push, or history rewrite is required;
- an unresolved P0/P1, conflict, failed required check, or scope drift cannot
  be resolved within the separately approved allowlist.

## Authorization gate

Approval of RFC-V7-009 authorizes only this docs-only design record and the
matching V7-11 roadmap entry. It does not authorize implementation, the GET
route, Web changes, runtime sidecar reads, database or directory access,
Page mutation, quality, approval, workflow transition, V7-09 changes,
Provider calls, generation, I02, dependencies, `main`, versioning, release,
tag, publication, Settings, branch deletion, force push, or history rewriting.

Any future implementation requires explicit approval of a revalidated exact
allowlist, the closed additive GET/DTO contract, the complete-history bounds,
and the applicable validation plan. Documentation acceptance alone grants no
runtime authority.
