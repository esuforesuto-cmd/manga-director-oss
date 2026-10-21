# RFC-V7-010: Durable Local Human Visual Review Evidence-Linked Approval

- Status: Complete and verified
- Target line: v7.0 Discovery (Post-LTS)
- Roadmap item: V7-12 Durable Local Human Visual Review Evidence-Linked Approval
- Delivery scope: completed exact twenty-one-file implementation
- Decision owner: an explicit local human approver

## Completion evidence

The exact twenty-one-file V7-12 implementation was completed in PR #48. Final
head `5835de2c5d890a40a232f1ff7ad9a7a690240eff` was merged into `v7-dev` at
`a02eedf38cd79c43c2add68ac08c332dab5eefb8`.

Full pytest passed with 3238 tests and 16 skips. Focused V7-12 and V6
public/LTS compatibility tests, Ruff, Windows/Linux mypy, Web
lint/typecheck/unit/build, mock and real-boundary browser E2E, security/audit,
package, clean-install, CLI/MCP/Plugin smoke, migration, whitespace, and
exact-allowlist checks passed. PR CI run #166 passed 10/10 jobs and PR CodeQL
run #65 passed 3/3 jobs. Post-merge CI run #167 passed 10/10 jobs and CodeQL
run #66 passed 3/3 jobs. Independent read-only review reported P0/P1/P2 =
0/0/0.

The feature branch remains retained. `main` remains unchanged at
`b0291437af05fe53454843ba95fdf88216700f7c`, and I02 remains out of scope. This
RFC remains the frozen design and completion record; completion grants no new
runtime, approval, workflow, release, or publication authority.

## Decision boundary

This RFC records the implemented smallest loopback-only boundary that lets a
local human explicitly approve one authoritative `QualityChecked` Page while
naming one exact immutable V7-10 human visual review evidence record.

The operation is additive. Existing ordinary approval remains available and
unchanged for compatibility. Evidence-linked approval never chooses a review,
copies a reviewer identity, infers approval, or changes the state transition.
The caller must explicitly provide both `approvedBy` and one exact `reviewId`.

Before the existing approval transition may run, the new private Application
gate must execute inside the durable LocalFile Page fence after the fresh
revision is loaded. It reads that exact record, binds it to the fenced
authoritative Page, requires the stored result to be `ready`, and recomputes
the same readiness result from the current exact generated asset while
retaining its safe file lease. Only an exact match may continue through the
existing `WorkflowEngine` and `StateMachine`.

The implementation added only the separately approved route, private service,
approval artifact reference, V7-09 closed-shape compatibility, explicit Web
action, and related tests. It added no database, dependency, migration,
StateMachine or WorkflowEngine change, or unrelated runtime authority.

## Problem

V7-10 stores immutable human visual review evidence and V7-11 displays the
complete bounded history without selection or approval meaning. The ordinary
approval action records only the explicit approver. A local approver cannot
currently create a durable approval artifact that names the exact review
evidence they deliberately relied on.

Automatically using the latest, newest, best, winning, or only record would
silently create policy and could bind approval to stale or unintended evidence.
Treating historical `ready` as approval would also violate the explicit human
approval boundary. Conversely, trusting the historical row without checking
the current authoritative Page and asset would allow a stale record to be
linked after the underlying delivery proof changed.

A separate explicit operation is therefore required. It must preserve ordinary
approval, reuse the immutable evidence store, re-prove current readiness, and
delegate the single `QualityChecked` to `Approved` transition to the existing
workflow owners.

## Planning summary

- **Title:** V7-12 Durable Local Human Visual Review Evidence-Linked Approval
- **Objective:** Let a local human explicitly approve one `QualityChecked` Page
  while durably naming one exact, current, `ready` V7-10 record.
- **Scope:** One LocalFile Project, one authoritative Page, one caller-selected
  review ID, one explicit approver reference, one private Application service,
  one additive loopback-only POST, and one explicit Web action.
- **Inputs:** Project ID and Page number from the route; exact `reviewId` and
  explicit `approvedBy` from a closed body.
- **Outputs:** The existing Page-detail response after the normal approval
  transition, with an additive evidence reference in the approval artifact; or
  one redacted fail-closed response with no Page or evidence mutation.
- **Dependencies:** Completed V7-07 through V7-11 and their frozen contracts.
- **Estimated complexity:** High for the completed separately approved
  implementation; Low for the original docs-only design.
- **Architecture notes:** The V7-10 owner reads exact evidence, V7-08 re-proves
  current readiness, a private Application service coordinates the lease and
  approval command, and existing workflow owners retain transition authority.

## Goals

- Require deliberate selection of one exact immutable review evidence record.
- Require a separate explicit approver reference; never infer it from reviewer
  evidence.
- Accept only a stored `QualityChecked`, `ready` record with no findings or
  missing prerequisites.
- Bind the record to the exact Project, Page ID, Page number, generation
  attempt, output asset, provenance, Visual QA result, and current safe file.
- Recompute readiness from the record's complete stored human submission and
  require canonical equality with the immutable stored payload.
- Retain the current exact generated-file lease until the durable approval save
  either succeeds or fails.
- Use the existing `StateMachine`, `WorkflowEngine`, durable LocalFile command
  route, and approval agent without bypassing or duplicating their authority.
- Preserve existing ordinary approval, V7-09 eligibility, public Python API,
  V6 LTS behavior, and all unrelated workflows.
- Keep failures deterministic, bounded, redacted, and mutation-free.

## Non-goals

- requiring evidence-linked approval for existing callers or existing Pages;
- changing or removing the ordinary approval route, request, response, or
  artifact;
- automatically selecting a latest, newest, best, winning, consensus, only,
  first, or last record;
- treating stored or recomputed `ready` as approval or as permission to invoke
  approval without a separate explicit human action;
- copying `reviewerId` into `approvedBy`, comparing those references, or
  treating either value as verified identity, authentication, or a role;
- approving a `Generated`, `Approved`, stale, missing, conflicting, corrupt,
  busy, unsafe, `needs_review`, or `blocked` record;
- changing the V7-10 schema, row, payload, digest, fingerprint, journal mode,
  append semantics, or evidence identity;
- writing, updating, deleting, replacing, repairing, compacting, vacuuming,
  checkpointing, or migrating review evidence;
- changing `Page`, `Project`, Repository, or LocalFile serialized schemas;
- changing StateMachine transitions, WorkflowEngine sequencing, automatic run,
  retry, rollback, or event-publication semantics;
- making review evidence a new V7-09 download eligibility rule;
- reopening, revoking, rejecting, reapproving, superseding, or amending an
  Approved Page;
- Provider construction or calls, generation, regeneration, fallback, remote
  fetch, DNS, proxy, redirect, or outbound network access;
- CLI, MCP, SDK, Plugin, public Python, LAN, wildcard, cloud, or remote
  surfaces;
- I02 or use of I02 state, authority, persistence, or recovery;
- dependencies, lockfiles, package metadata, versioning, release, tag,
  publication, Settings, `main`, force push, history rewrite, or branch deletion.

## Source contracts

The implemented feature composes only these existing owners:

- the authoritative LocalFile Project supplies the exact Page identity, current
  `QualityChecked` state, current workflow artifacts, and durable save boundary;
- the V7-10 production owner privately reads and fully validates one exact
  immutable evidence record by caller-supplied `reviewId`;
- the V7-08 readiness service resolves the current exact generated asset,
  validates generation and QA evidence, recomputes the report, and retains the
  exact-file lease;
- the new private Application gate compares the stored and recomputed canonical
  payloads against the freshly fenced authoritative context and retains the
  proof lease;
- the existing durable LocalFile workflow route owns the Page fence, invokes
  that gate before workflow execution, applies one closed approval input, and
  persists the resulting Page;
- the existing approval agent creates the approval artifact;
- the existing `WorkflowEngine` and `StateMachine` remain the sole transition
  authorities; and
- HTTP and Web remain presentation adapters with no evidence-selection or
  approval policy.

No Web component, stored status, timestamp, row order, record count, or reviewer
reference independently authorizes approval.

## Frozen architecture

### Explicit evidence-linked approval operation

The separately approved implementation added exactly one logical operation:

`POST /projects/{project_id}/pages/{page_number}/evidence-linked-approval`

Its closed JSON request contains exactly:

- `approvedBy`: a non-empty explicit human approver reference; and
- `reviewId`: one non-empty exact logical V7-10 evidence reference.

Unknown fields, a generic `metadata` object, query parameters, duplicate JSON
members, missing values, non-string values, leading or trailing whitespace,
control characters, and out-of-bound values fail before Project or evidence
access. `approvedBy` and `reviewId` are independent; neither is derived from or
compared with `reviewerId`.

The response reuses the existing `PageDetailDTO` after the normal durable
approval succeeds. No evidence payload, reviewer-authored text, internal
binding, filesystem detail, or proof object is returned by the approval route.

The existing generic approval remains unchanged:

`POST /projects/{project_id}/pages/{page_number}/approve`

It neither accepts nor creates an evidence link. Existing CLI, MCP, SDK,
Plugin, public Python, and non-LocalFile approval behavior remain unchanged.

### Browser write admission

Before Project or sidecar access, the new route requires the same strict local
browser-write admission class as the implemented V7-10 record operation:

- one exact allowed local `Origin`;
- one allowed local `Referer` with the same parsed origin;
- `Sec-Fetch-Site: same-origin`;
- `Sec-Fetch-Mode: cors`;
- `Sec-Fetch-Dest: empty`; and
- explicit JSON `Content-Type` and `Accept` values.

The route rejects transfer encoding, missing or duplicate admission headers,
conditional headers, range headers, query parameters, invalid body framing,
non-canonical raw Page numbers, and remote or LAN callers. CORS is transport
policy only and never approval authority.

### Exact record selection

The caller supplies exactly one `reviewId`. The service performs one exact-ID
read through the V7-10 owner. It does not enumerate history, fall back to
another ID, or select by row order, timestamp, status, reviewer, Page state,
output asset, or perceived quality.

The V7-10 owner opens only the existing database with its implemented
read-only/query-only discipline, exact schema and row validation, bounded work,
safe path checks, rollback-journal policy, canonical digest validation, and
redacted failure behavior. An absent store or record is unavailable, not an
empty or replaceable approval input.

The selected record must match the authoritative Project ID, Page ID, and Page
number exactly. Its recorded Page state must be `QualityChecked`; a record made
while the Page was merely `Generated` cannot support this operation even if its
historical status says `ready`.

### Ready record requirements

The stored payload must have all of the following closed properties:

- `status` is exactly `ready`;
- `ready` is exactly `true`;
- findings are empty;
- missing prerequisites are empty;
- the checklist is complete and canonically ordered; and
- the overall judgment and every checklist decision satisfy the existing V7-08
  readiness contract.

These requirements apply only to the optional evidence-linked approval
operation. They do not redefine historical evidence, ordinary approval, Page
state, or V7-09 eligibility.

### Current re-proof and canonical equality

Historical validity alone is insufficient. After the durable LocalFile
coordinator has acquired the Page fence and loaded the fresh revision, it must
invoke the private Application gate with that authoritative context. Using only
the selected immutable record's complete stored human submission, the gate
asks the existing V7-08 readiness service to re-prove the same current Page.

The re-proof must resolve the current authoritative Page and exact generated
asset, validate the existing generation evidence and Visual QA bindings, and
retain the existing safe exact-file lease. The service reconstructs the same
V7-10 canonical payload from the recomputed report and requires complete exact
equality with the stored payload, including identity bindings, record identity,
human submission, Page state, status, findings, and missing prerequisites.

The Page identity, state, approval absence, image artifact, quality artifact,
and workflow history used by the re-proof must equal the freshly loaded fenced
context. Any changed Page revision, identity, state, attempt, output,
provenance, QA reference, asset identity, bytes, human submission, derived
status, finding, missing prerequisite, digest, or binding fails closed. There
is no pre-fence proof, refresh, tolerance, normalization, partial comparison,
or substitution.

### Lease and durable approval ordering

The exact-file lease obtained by the in-fence current re-proof remains held
while the normal durable LocalFile approval command executes. The same Page
fence remains held from fresh revision load through validation, transition,
conditional commit, post-commit verification, and event publication. The proof
lease is released before the Page fence and only after the existing durable
operation has reached its terminal success or failure outcome and cleanup has
completed.

The immutable evidence store is never locked for writing and is never changed.
Failure before conditional commit leaves the Page unchanged. A post-commit
verification or event-publication failure may leave the Page durably Approved,
exactly as the existing durable execution contract already permits. The route
must return the existing bounded failure outcome, must not claim success from
the failed request, and must rely on authoritative reload and the existing
recovery contract. V7-12 adds no compensation, retry, rollback claim, or
alternate save path, and no failure may add or change an evidence row.

### Reserved approval input and artifact

The review evidence reference is a reserved server-owned approval input. Every
generic/public approval entry point rejects or removes it; caller-supplied
generic metadata cannot forge an evidence-linked approval. Only the new private
Application service may supply it after exact validation and current re-proof.

Ordinary approval continues to persist exactly:

`{"approved_by": "<explicit approver>"}`

Evidence-linked approval persists exactly:

`{"approved_by": "<explicit approver>", "review_evidence_id": "<exact review>"}`

The additive field is a reference only. It does not copy the evidence payload,
reviewer text, status, timestamp, digest, path, or approval policy into the
Project. `Page.approval` remains the existing mapping field; the Page and
Project model schemas do not change. Legacy persisted Pages remain valid.

### Workflow authority

The new service does not set Page state, construct workflow events, call the
approval agent directly, or save a Page directly. It submits one closed approval
command and one private validation gate through the existing durable LocalFile
path. The coordinator invokes the gate only after acquiring the existing Page
fence and loading the fresh revision, and before calling the WorkflowEngine.

The existing StateMachine must still authorize only the
`QualityChecked -> Approved` transition. The existing WorkflowEngine must still
resolve and execute the approval agent and publish its canonical event. V7-12
changes neither component.

### V7-09 compatibility

V7-09 must continue to determine download eligibility only from the existing
conditions: authoritative `Approved` state, a valid explicit `approved_by`, and
the existing exact safe generated-asset proof.

Its closed approval-artifact validation may accept either the legacy exact
shape or the evidence-linked exact shape. It validates the optional logical
reference when present but must not require it, dereference it, read the V7-10
store, choose evidence, or use it to grant or deny eligibility. No legacy Page
is migrated.

### Explicit Web behavior

The V7-11 history panel may expose an evidence-linked approval control only for
an explicitly loaded `ready` record while the current authoritative Page is
`QualityChecked`.

- History loading remains an explicit read and selects nothing by default.
- Every record is initially unselected.
- Only a deliberate action on one exact displayed `ready` record supplies its
  `reviewId` to the linked-approval form.
- The operator separately enters `approvedBy`; `reviewerId` is never copied,
  suggested, or used as a default.
- The UI labels the action as approval linked to the named historical record;
  viewing or selecting the record does not approve the Page.
- The existing ordinary approval form remains available and visibly unlinked.
- One submit produces one request; there is no auto-submit, polling, retry,
  queue, optimistic state change, or background action.
- On success the Page is refreshed from the server. On failure the UI displays
  one generic error and does not claim approval.

Reviewer-authored text remains rendered as escaped text and never becomes HTML,
Markdown, a URL, path, header, log value, command, or authorization input.

## State behavior

| Current authoritative Page state | Evidence-linked approval behavior |
| --- | --- |
| `Draft` through `Generated` | Fail closed; no approval transition is attempted. |
| `QualityChecked` | Validate one exact record, re-prove current readiness, then request the existing approval transition. |
| `Approved` | Fail closed; do not amend, relink, revoke, or reapprove. |

The selected record must itself store `pageState: QualityChecked`. Current Page
state and stored record state are independently checked.

## Mutation boundary

On success, exactly the existing durable approval transaction may change:

- the authoritative Page state from `QualityChecked` to `Approved`;
- the existing approval artifact, adding only the exact selected evidence
  reference beside the explicit approver;
- the existing workflow history/current-step metadata; and
- the existing canonical approval event and durable execution records.

Success changes no V7-10 database byte, row, schema, directory, journal, or file
metadata under application control. A failure before conditional commit leaves
the Page unchanged. After conditional commit, post-commit verification or event
publication may fail while the Page remains durably Approved; the response and
subsequent recovery must preserve the existing durable execution semantics and
reload the authoritative Page rather than compensate, retry, or claim rollback.
The evidence store remains unchanged on every failure path.

## Security and privacy

- Server binding and CORS remain loopback-only.
- Closed request, logical-reference, body-size, and raw Page-number bounds apply
  before Project or sidecar access.
- The exact record is read only through the V7-10 owner; HTTP/Web never sees
  internal payload fields required solely for validation.
- The current generated file remains protected by the existing safe LocalFile
  proof and lease against replacement races.
- Generic approval metadata cannot forge the reserved link field.
- No reviewer-authored value becomes approver identity, HTML, Markdown, path,
  header, log format, SQL, credential, role, or permission.
- Success and error responses use `Cache-Control: no-store` and
  `X-Content-Type-Options: nosniff` and emit no validator or redirect metadata.
- Errors reveal no reviewer text, internal binding, digest, Provider, path,
  storage name, root, database, SQL, traceback, or proof details.
- No authentication, role system, audit publication, analytics, telemetry,
  notification, secret, browser persistence, or remote access is added.

## Determinism

For the same explicit inputs and unchanged authoritative Project, evidence
store, generated asset, and durable workflow state, the pre-approval decision
and linked approval artifact are identical.

Current time, row order, history count, locale, filesystem enumeration, random
choice, environment preference, browser state, Provider result, or network
result cannot select or alter the record. Concurrent change, ambiguity, busy
storage, or proof mismatch fails the operation instead of choosing a fallback.

## Failure and recovery semantics

All failures are redacted and fail closed:

- invalid local admission or malformed request returns a validation failure
  before Project or evidence access;
- missing Project, Page, store, or exact record returns the route's closed
  not-found/unavailable class without revealing which internal object is absent;
- non-`QualityChecked` state, non-ready stored evidence, binding mismatch,
  corrupt or busy storage, current re-proof failure, or canonical mismatch
  prevents workflow execution;
- approval transition, durable save, or event-publication failure follows the
  existing durable execution outcome and recovery contract, including the
  possibility of a durably committed Page after a later failure; and
- every path releases the safe asset lease exactly once.

There is no alternate evidence, partial validation, ordinary-approval fallback,
automatic retry, repair, migration, state override, or direct Page save.

## Public contract compatibility

The implemented feature is one additive local HTTP/Web operation and one
additive optional field in the approval artifact created only by that
operation.

Existing ordinary approval inputs and outputs, V6 public imports, CLI, MCP,
SDK, Plugin, Provider, Repository protocols, LocalFile serialized model schema,
StateMachine, WorkflowEngine, V7-08 assessment, V7-10 recording, V7-11 history,
and legacy persisted Pages remain unchanged. No new package export is permitted.

## Docs allowlist

This completion-state update is limited to exactly two files:

1. `docs/RFC_V7_010_DURABLE_LOCAL_HUMAN_VISUAL_REVIEW_EVIDENCE_LINKED_APPROVAL.md`
2. `docs/ROADMAP_V7.md`

A third docs file is a scope expansion and requires explicit approval.

## Implementation allowlist

The implementation was completed within the separately approved exact
twenty-one files:

1. `src/manga_director/application/evidence_linked_approval.py` (new)
2. `src/manga_director/application/workflow.py`
3. `src/manga_director/agents/builtin.py`
4. `src/manga_director/workflow/durable_execution.py`
5. `src/manga_director/application/approved_asset_download.py`
6. `src/manga_director/api/composition.py`
7. `src/manga_director/api/workflow.py`
8. `tests/test_evidence_linked_approval.py` (new)
9. `tests/test_safe_local_approved_asset_download.py`
10. `tests/test_workflow_application.py`
11. `tests/test_localfile_primary_durable_routing.py`
12. `tests/test_workflow_http_api.py`
13. `tests/unit/test_agents.py`
14. `web/lib/api/types.ts`
15. `web/lib/api/client.ts`
16. `web/components/human-visual-review-evidence-history.tsx`
17. `web/components/page-workflow.tsx`
18. `web/tests/api-client.test.ts`
19. `web/tests/ui-contract.test.ts`
20. `web/e2e/mock-api.mjs`
21. `web/e2e/workflow.spec.ts`

The V7-10 store, V7-08 readiness service, V7-10 evidence writer, V7-11 history
service, Page/Project models, repositories, StateMachine, WorkflowEngine,
dependencies, lockfiles, package metadata, Provider, generation, CLI, MCP, SDK,
Plugin, and I02 are excluded. No twenty-second file was required. Any future
twenty-second implementation file is a scope expansion.

## Validation plan

This completion-state update requires:

- exact two-file docs allowlist verification;
- Markdown link resolution and `git diff --check`;
- zero source, test, dependency, lockfile, package, version, Settings, or
  `main` diff;
- architecture, approval authority, durable execution, LocalFile safety,
  privacy, V7-09 compatibility, public-contract, and V6 LTS review; and
- independent read-only review with P0 = 0 and P1 = 0.

The completed implementation passed focused tests for:

- exact explicit `reviewId` selection and no default/latest/best behavior;
- closed local write admission and closed request DTO behavior;
- authoritative Project/Page/state binding and stored `QualityChecked` state;
- stored ready/non-ready, findings, and missing-prerequisite handling;
- exact current re-proof equality across attempt, output, provenance, QA,
  asset identity/bytes, submission, status, and bindings;
- proof execution against the freshly loaded revision inside the same Page
  fence, including pre-fence and concurrent-change rejection;
- lease retention through durable success, failure, rollback, and cleanup;
- pre-commit failure versus post-commit verification/event failure, including
  authoritative reload with no compensation or duplicate transition;
- reserved-input anti-forgery through generic HTTP, Application, and metadata
  paths;
- ordinary approval compatibility and unchanged legacy artifact shape;
- evidence-linked approval artifact persistence across restart;
- V7-09 legacy and linked artifact acceptance with identical eligibility;
- no evidence-store mutation on success or failure;
- no workflow call before all evidence checks pass;
- no StateMachine/WorkflowEngine change, bypass, retry, or direct save;
- explicit Web selection, separate approver input, no reviewer copy, no
  auto-submit, and ordinary approval availability;
- redaction, request/response headers, no cache, no remote surface, and no
  Provider/generation/I02 action; and
- focused/full Python, Ruff, Windows/Linux mypy, Web lint/typecheck/unit/build,
  mock and real-boundary browser E2E, security/audit, package, clean-install,
  CLI/MCP/Plugin smoke, V6 compatibility, exact-allowlist, and whitespace gates.

## Acceptance criteria

V7-12 is complete and verified because:

1. One explicit local request supplies one exact review ID and one separate
   explicit approver reference.
2. No review is selected automatically or inferred from history.
3. Only an exact immutable stored `QualityChecked`/`ready` record with no
   findings or missing prerequisites may proceed.
4. Current readiness is re-proved against the freshly loaded authoritative
   revision inside the existing Page fence and must reproduce the stored
   canonical payload exactly.
5. The exact-file lease remains held through conditional commit, verification,
   and event publication, is released exactly once, and no pre-fence proof may
   authorize approval.
6. The existing StateMachine and WorkflowEngine remain the only transition
   authorities and are not modified.
7. Ordinary approval remains unchanged and cannot forge an evidence link.
8. Linked approval persists only `approved_by` plus the exact
   `review_evidence_id`; it copies no evidence or reviewer-authored content.
9. V7-09 accepts legacy and linked approval artifacts but uses identical
   eligibility rules and never reads review evidence.
10. V7-10 evidence and V7-11 history remain immutable and unchanged.
11. Project/Page model schemas, repositories, public Python, CLI, MCP, SDK,
    Plugin, Provider, generation, dependencies, I02, v5, and v6 remain
    unchanged.
12. The implementation stayed within its approved exact twenty-one-file
    allowlist and passed focused/full regression, Web, security, package, CI,
    CodeQL, and post-merge gates with no blocking failure.
13. This completion-state diff stays within the exact two-file docs allowlist
    and independent review reports no P0/P1 issue.

## STOP conditions

Any follow-up must stop on any of the following:

- a third docs file or a twenty-second implementation file is required;
- the V7-10 schema, row, payload, digest, fingerprint, journal, identity, or
  append contract must change;
- automatic record selection, inferred approval, reviewer-to-approver copy, or
  ordinary-approval fallback is required;
- the evidence store must be written, repaired, migrated, compacted, vacuumed,
  checkpointed, or normalized;
- Page/Project/Repository/LocalFile model schema or public API must change;
- StateMachine or WorkflowEngine must change or be bypassed;
- V7-09 eligibility must depend on review evidence;
- Provider, generation, remote access, I02, dependency, lockfile, package,
  version, release, tag, publication, Settings, or `main` must change;
- branch deletion, force push, or history rewrite is required; or
- an unresolved P0/P1, failed required check, merge conflict, or scope drift
  cannot be resolved inside the separately approved allowlist.

## Authorization gate

V7-12 is complete. Its separately approved exact twenty-one-file
implementation authorization was exhausted by PR #48. It does not authorize a
twenty-second file, another route or Web change, evidence-store or schema
change, another approval behavior, V7-09 eligibility change, StateMachine or
WorkflowEngine change, Provider, generation, I02, dependencies, `main`,
versioning, release, tag, publication, Settings, branch deletion, force push,
or history rewriting.
