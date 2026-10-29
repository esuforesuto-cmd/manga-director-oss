# RFC-V7-013: Safe Local Panel-Aware Generation Activation

- Status: Slices 1 and 2 complete and merged; Slice 3 implementation is in progress under the separately approved 17-file local implementation scope
- Related roadmap item: V7-15 Safe Local Panel-Aware Generation Activation
- Baseline: `v7-dev` commit `6b956bbad0bda801ae696786fa93a76b9e850fb2`
- Prerequisite: V7-14 Complete and verified; remote/public deployment disabled
- Public activation: dedicated LocalFile HTTP route implemented; Web and remote activation remain disabled
- Authentication: unchanged and absent; loopback, CORS, and same-origin checks are not authentication
- Live Provider/ComfyUI: not authorized

## Summary

V7-15 provides an explicitly activated LocalFile path from a `PromptBuilt`
Page to the completed private V7-14
`PanelAwarePageGenerationOperation`. Slice 2 exposes panel-aware generation as
a separate HTTP route; Slice 3 remains an explicit Web action. The route
preserves the existing generic `/generate` action and its behavior unchanged.

The private application entry point will take one authoritative revisioned
Page snapshot, explicit user attribution (`authorizedBy`), a verified
`checkpointName`, and explicit panel rectangles for the supported V7-13 layout
profile. It will use the real V7-04 checkpoint/configuration validation path,
V7-14 conversion/operation binding, and V7-13 durable mode, attempt,
composition, and application authorities. Browser input will never select an
authorization ID, attempt ID, provider endpoint, workflow graph, or transport
configuration.

This RFC freezes the design boundary and staged plan only. It does not authorize
code, HTTP, Web, configuration, schema, dependency, or persistence changes.

## Context and Current Contracts

- V7-13 owns Page-mode exclusion, the durable mode claim, panel reservations
  and provider-start, recovery, composition, output proof, and its frozen DTOs.
- V7-14 converts the exact persisted Storyboard and PromptBuilt artifacts,
  constructs the fully bound private operation, and adapts its provider port to
  the existing V7-04 private ComfyUI transport. Its public routing remains
  disabled.
- V7-04 owns checkpoint/configuration validation, the fixed graph, loopback
  transport, preflight, prepared invocation, PNG validation, and output
  registration. V7-15 must not create a second transport or weaken these gates.
- The current HTTP workflow route is `/projects/{project_id}/pages/{page_number}/{action}`;
  its `generate` action remains the legacy workflow command. It is not the
  panel-aware activation route.
- The current Web workflow action list presents the generic “Generate” action.
  Panel-aware activation must be an additional, explicit “Generate panels”
  action and must not infer a layout from Storyboard content or screen size.
- `StateMachine` owns the legal `PromptBuilt -> Generated` transition. The
  existing WorkflowEngine/StateMachine/EventBus/CAS path remains the only Page
  state transition authority.

## Goals

1. Provide one private LocalFile application operation that starts generation
   only from a `PromptBuilt` Page, prepares the exact V7-14 operation from one
   revisioned snapshot, and invokes the existing V7-13 operation. An already
   `Generated` Page may enter only the read-only replay verification below.
2. Apply `PromptBuilt -> Generated` through a dedicated safe application
   adapter that preserves the existing StateMachine, EventBus, CAS, durable
   output proof, and application-ledger semantics.
3. Add a distinct HTTP route with a closed request model. Public input is
   limited to `authorizedBy`, a validated `checkpointName`, and explicit
   ordered panel rectangles/profile selection. Project and Page identity come
   from the route; source narrative and prompt content come only from the
   persisted Page snapshot.
4. Add an explicit Web “Generate panels” action. The user must provide/confirm
   the supported panel geometry; Web code must not create, estimate, or infer
   rectangles.
5. Bind pre-transition retries to the same exact Page revision, request, mode
   claim, authorization references, reservations, and V7-14 operation. After
   the Page becomes `Generated`, return only a verified bounded replay result
   or fail closed, as specified below. No retry creates another provider
   attempt; changed input must fail closed.
6. Keep all provider calls behind V7-04 and test with fakes only.

## Non-goals

- Changing the generic `/generate` route, its request/response behavior, or
  legacy single-canvas mode.
- Exposing V7-13/V7-14 DTOs, authorization/attempt IDs, provider references,
  endpoint URLs, graph data, credentials, or transport details to HTTP/Web.
- Inferring panels, choosing a layout, generating rectangles, editing
  Storyboard/PromptBuilt fields, or using an LLM to fill missing data.
- Changing V7-04 transport/security/configuration authority or V7-13 frozen
  DTOs, durable authorities, recovery, mode admission, or persistence schema.
- Adding a new database/schema/migration, dependency, lockfile, export, public
  SDK/MCP/CLI/Plugin contract, or alternate persistence authority.
- Automatic retries, provider fallback/switching, multiple provider calls for
  one reserved panel, or live ComfyUI/provider tests.
- I02, `main`, release, package publication, external/public deployment, or
  branch operations.

## Proposed Request and Authority Boundary

The proposed dedicated route is
`POST /projects/{project_id}/pages/{page_number}/panel-aware-generation`.
Register this fixed route before the existing `/{action}` route so that
`panel-aware-generation` reaches its dedicated handler, never the legacy
action dispatcher.
Its request is closed (`extra=forbid`) and versioned. It carries only:

- `authorizedBy`: bounded human attribution, treated as attribution rather
  than proof of authentication or permission;
- `checkpointName`: a checkpoint identifier validated by the existing V7-04
  validator and the applicable real V7-04 configuration/preflight path;
- an exact supported layout profile/version and one explicit integer rectangle
  per persisted panel, in canonical panel order.

No client-provided IDs, endpoint, graph, prompt, panel text, or hidden
`metadata` bag is accepted. Route `project_id` and `page_number` must be
canonical and must match the revisioned LocalFile snapshot. The application
must reject an incorrect Page state, incomplete source fields, stale or mixed
snapshot, invalid geometry, unsupported checkpoint/configuration, or any
binding mismatch before provider activity.

The private application activation service is the only issuer of the safe
per-panel and composition authorization references consumed by RFC-V7-012.
It must derive them deterministically from the canonical closed activation
binding and validated author attribution, before dependent attempt/composition
IDs are derived. The references are independent of those IDs, stable for an
identical authorized activation, and bound to its exact verified Page revision
and closed request; existing V7-13 durable authorities must confirm/persist
the exact bindings. This application-side issuance adds no separate persistence
authority. The server must not accept or trust an authorization reference
supplied by a browser. If these properties cannot be met while preserving
RFC-V7-012's already-issued-reference rule and existing V7-13/V7-14 contracts,
stop and seek a revised scope. `authorizedBy` alone does not establish
authentication or permission; deployment authorization is an explicit
prerequisite and cannot be invented by this RFC.

The server also determines `PageGenerationModeClaim.claim_id` and
`authorizer_reference` stably from the same canonical activation binding and
validated attribution. They are not client inputs. The claim directly binds
the original Page revision/fingerprint and its exact plan; retries may not
substitute a claim, authorizer, or authorization reference.

### State-dependent Retry and Replay Contract

Use only existing V7-13 durable authorities and their verified records. Do not
add a client-controlled idempotency key, schema/migration, cache, or separate
persistence authority. A retry follows the observed state:

| Observed state | Required result |
| --- | --- |
| `PromptBuilt`, same original revision and identical canonical activation input | Resolve to the same stable server-issued references, mode claim, V7-14 operation, and reservations. Existing authorities decide admission/recovery; no replacement attempt is created. |
| Same exact authoritative `RESERVED` reservation, provider-start unconsumed | A later explicit retry may repeat only bounded read-only preflight/preparation for that reservation, then follow the existing recheck/start/submit boundary. |
| Provider-start consumed and outcome uncertain | Return `recovery_required`; no resubmit, fallback, replacement attempt, or state reset. |
| Page already `Generated` after successful CAS, including a lost HTTP response | Enter only read-only replay verification under the existing Page fence. Return a bounded `already_generated` result with zero provider calls and no Page/CAS/EventBus/application-ledger write only if the exact original activation and completed success binding can be recovered and verified from existing durable records. Otherwise return `revision_conflict` and stop. |
| Changed body, geometry, checkpoint, `authorizedBy`, source revision/fingerprint, or Page binding; missing/ambiguous/corrupt authority | Fail closed without creating a second executable attempt or treating the request as the existing success. |

Successful CAS advances the LocalFile revision and changes the Page to
`Generated`. Do not pass this new snapshot to the V7-14 builder as if it were
the original `PromptBuilt` snapshot, reconstruct a historical snapshot by
rewriting the current Page, or infer the old revision by decrementing it.
For `already_generated`, recover the original claim/revision and exact
operation binding from verified existing records, and compare the submitted
closed input, including attribution, checkpoint and geometry, to that original
activation. Verify the current output asset against the exact mode claim,
accepted panel/evidence records, completed composition/evidence, composite
asset, and completed application-ledger binding using existing authorities.
The original source binding and every input needed to verify its identity must
be recoverable; Page state or output asset alone is insufficient. If that exact
recovery or any comparison is unavailable, return `revision_conflict` with zero
provider calls. This is a safe refusal, not a promise to reconstruct every
successful operation. No new persistence or authority change is permitted to
make replay possible.

## Activation Sequence

1. Parse the dedicated closed request; reject unknown fields, invalid scalar
   types, aliases, overlong values, and non-canonical route identifiers.
2. Observe one authoritative revisioned LocalFile snapshot under the existing
   Page execution fence. If already `Generated`, perform only the read-only
   replay verification above and return. Otherwise require `PromptBuilt` and
   bind generation to that exact snapshot. Preserve the existing authorities'
   fence acquisition/recheck boundaries.
3. Validate `checkpointName` using the real V7-04 validation/configuration
   service. Do not construct a “ready” validation object or bypass preflight.
4. Validate the explicitly supplied profile/version and rectangles against
   V7-13's frozen geometry rules and exact persisted panel order. Do not infer
   or repair geometry or source text.
5. Issue/reconfirm stable server-side authorization references for this exact
   activation before deriving IDs that depend on them. Build the complete
   V7-14 operation with the same snapshot, issued references, and validated
   checkpoint. Keep all V7-13/V7-14 identity and evidence derivations exact.
6. Execute through the V7-13 mode admission, durable panel reservation,
   V7-04 read-only preflight/prepare, post-prepare authority recheck, durable
   provider-start, and one prepared submit sequence. No POST may happen before
   durable provider-start. Each panel is submitted at most once; no retry,
   fallback, or provider switch follows start.
7. On accepted composition, use a dedicated application adapter to apply the
   existing generated-page proof through WorkflowEngine/StateMachine, EventBus,
   CAS, and the existing durable application ledger. Do not directly mutate
   Page state or bypass the existing `generate` transition authority.
8. Return a bounded route-specific result. Do not return private IDs, provider
   configuration, endpoint information, raw graph, or internal exception text.

## Web Behavior

The existing “Generate” action remains unchanged. The panel-aware control is
separate and labeled “Generate panels”. It is offered only when the Page is
eligible and the application can present the explicit geometry input flow.
The user explicitly supplies or confirms one rectangle per panel for the
supported profile. The Web client sends only the closed public fields above
and never submits derived IDs or provider details. It does not derive layout
from panel count, screen dimensions, or conventional grid assumptions. On
unsupported/missing layout, it explains that generation is unavailable until
valid explicit geometry is provided; it does not silently fall back to legacy
Generate.

## Slice Plan and Approval Gates

Slice 1 was separately approved and is complete and verified as recorded in
the Asset-ID Registration Amendment and Slice 1 Completion Evidence below.
Slice 2 was separately approved with the exact seven-file allowlist on
2026-10-28. Slice 3 is separately authorized under the exact 17-file allowlist
recorded in the active implementation task.

### Slice 1 — Local/Application Activation

Compose the private activation service from the V7-14 converter/operation
builder, V7-13 operation/authorities, and real V7-04 validation path. Add the
dedicated safe generated-application adapter that preserves existing state
transition and durable application semantics. No HTTP or Web route is enabled
in this slice. Tests use fake provider/transport, fake clock where applicable,
and temporary LocalFile roots; never localhost:8188 or live ComfyUI.

### Slice 2 — HTTP Route

The dedicated route and strict public DTO are implemented in the approved
LocalFile HTTP composition and map blocked/recovery outcomes to bounded
responses. Generic `/generate` remains unchanged. The request requires
`requestVersion: 1`, `authorizedBy`, a validated `checkpointName`, the exact
supported layout profile/version, and explicit ordered integer rectangles.
Unknown fields, duplicate JSON members, non-canonical path values, query
parameters, oversized bodies, and requests outside the existing same-origin
browser admission are rejected. The route adds no authentication; local
same-origin checks and CORS are not identity or authorization proof.

The local verification plan covers closed input, canonical route/page binding,
mode conflict, stable identical replay, changed request conflict, and proof
that no public fields control IDs or transport.
Register the fixed route before `/{action}`. Route-level tests must prove the
dedicated handler is reached without invoking the legacy action dispatcher,
and that `/generate` retains its handler, request DTO, and response contract.
Cover a lost successful response followed by an identical retry: verified
`already_generated` or fail-closed `revision_conflict`, both with zero provider
calls; never rebuild from the new `Generated` snapshot.

### Slice 3 — Web Activation

Add the explicit “Generate panels” interaction and user-entered/confirmed
geometry for the supported profile. Keep legacy “Generate” intact. Bind a
same-origin Next.js proxy to a fixed loopback API destination, validate browser
request metadata and exact body bytes, and forward only a strict header
allowlist without redirects. Browser Web Locks and a persistent per-Page
marker reduce accidental duplicate submissions across tabs and reloads; they
are not durable authority, and uncertain results remain blocked in the UI.
The existing V7-13/V7-15 authorities remain responsible for actual at-most-once
provider-start and recovery. Test no inferred layout, exact ordered rectangles,
errors, accessibility, reload/multi-tab and uncertain network outcomes. No
automatic grid or layout defaults.

## Invariants and Fail-Closed Conditions

- One immutable revisioned `PromptBuilt` snapshot is the source for conversion,
  operation identity, mode claim, and Page application. A mismatch or stale
  snapshot blocks generation. A `Generated` retry is limited to the read-only
  replay contract above and cannot use its new snapshot to build an operation.
- RFC-V7-012 canonical derivation rules remain authoritative for all plan,
  request, authorization-dependent attempt, evidence, composition, asset, and
  application bindings. V7-13 DTOs remain unchanged.
- Existing legacy and panel-aware generation remain mutually exclusive under
  the existing V7-13 mode authority.
- V7-04 remains the only ComfyUI transport/security authority and validates
  the real provider configuration and checkpoint. No alternate endpoint or
  graph is accepted from the caller.
- All preflight and preparation are read-only and complete before durable
  provider-start. No POST before successful start; exactly one prepared submit
  per attempt; uncertain post-start outcomes enter existing recovery-required
  handling with no resubmit.
- A preparation failure leaves the exact attempt `RESERVED`. A later explicit
  replay may repeat only bounded preparation for the same authoritative
  `RESERVED` record with unconsumed provider-start. No replacement attempt is
  created. After start, no retry or fallback.
- A generated Page transition occurs only through the existing StateMachine,
  EventBus, CAS, and durable application boundary with its accepted output
  proof. No direct Page mutation or second state authority.
- Missing/invalid concrete source fields, unsupported/missing/overlapping
  rectangles, invalid checkpoint/configuration, unavailable issuer/authority,
  ambiguous records, revision drift, binding mismatch, stale Page state,
  provider error, or any security uncertainty stops activation without
  fallback.

## Validation Plan

All provider-boundary validation uses fakes/mocks and temporary LocalFile
storage. No test or smoke check may call live ComfyUI or `localhost:8188`.

For each approved slice, select focused checks from:

- deterministic operation construction from one revisioned snapshot; exact
  request, reservation, mode claim, authorization, Page revision/fingerprint,
  composition/evidence/asset/application binding; golden vectors remain literal
  where RFC-V7-012 requires them;
- invalid/missing fields, rectangles, checkpoint, unsupported profile,
  alias identifiers, extra HTTP fields, and stale/mixed snapshot rejection;
- real validation-service wiring (fake its external boundary as needed),
  proving no `model_construct(...ready=True)` production shortcut;
- at-most-once, no fallback/retry, no POST before durable start, exact
  `RESERVED` re-preparation, authority recheck, restart/recovery and uncertain
  post-start results;
- same-request pre-transition replay resolving to the same references,
  claim/authorizer and operation; lost successful response after CAS and process
  restart yielding only a fully verified `already_generated` or fail-closed
  `revision_conflict`, with zero provider calls/writes; changed body, geometry,
  checkpoint, attribution or Page binding rejected; unavailable original
  binding and mismatched output/claim/panel/composition/application records
  rejected without a new attempt;
- route-level proof that the fixed panel-aware route precedes `/{action}` and
  reaches its dedicated handler; generic `/generate` handler/DTO/response
  contract regression tests;
- generated Page application through StateMachine/EventBus/CAS and existing
  ledger, including rejected transition and CAS conflict;
- Web explicit action, no inferred/automatic rectangles, public payload field
  allowlist, accessible interaction, and unchanged legacy action;
- relevant regression suites, Ruff, formatter check, mypy, pip-audit/security
  audit, and `git diff --check`, as applicable to the approved slice.

Passing tests do not authorize live ComfyUI, I02, public deployment, release,
or publication.

## STOP Conditions

Stop and submit a revised design and allowlist before implementation if any
slice requires changing V7-04 transport/security or V7-13 frozen DTO/durable
authority; adding a schema/migration, dependency/lockfile, export, or second
persistence authority; modifying generic `/generate`; exposing IDs/provider
details; deriving or persisting layout; changing Storyboard/PromptBuilt
production; bypassing real V7-04 validation, StateMachine, EventBus, CAS, or
application ledger; or accepting a stale, mixed, ambiguous, or mismatched
binding.

Stop before any provider start if authorization references cannot be issued
stably and independently of dependent IDs, a validated checkpoint/configuration
is unavailable, exact explicit geometry/source fields are absent, mode or
durable admission conflicts, or Page revision changes. If preparation fails,
do not start or submit; preserve the same `RESERVED` record. If outcome after
durable start is uncertain, record/use existing recovery-required handling and
never resubmit. A `Generated` retry may only perform the read-only replay
verification above; unavailable original activation binding or any comparison
failure returns `revision_conflict` without provider calls or writes. Any need
for live ComfyUI, I02, `main`, release/publication,
dependency/schema changes, branch deletion, or another public surface requires
separate explicit authorization.

## Authorization Gate

Slice 1 is complete and verified. Slice 2 was implemented and merged under
separate approval. Slice 3 implementation is authorized only within the exact
17-file allowlist and validation plan supplied for the current task. Live ComfyUI, I02, `main`, release/publication,
dependency/lockfile, schema/migration, or branch operations are not authorized
by this RFC.

## Asset-ID Registration Amendment and Slice 1 Gate (2026-10-28)

Status: implemented and verified as V7-15 Slice 1 under PR #65. The approved
Slice 1 scope comprised the six implementation/test files listed below plus
the three approved documentation/specification files, nine files total. This
completion records delivery of the amendment without changing its technical
requirements. Public routing remains disabled.

Apply RFC-V7-012's Asset-ID Registration Contract Amendment: the existing
server-derived canonical `panel-asset-v7-014-*` ID is the exact
`LocalDurableAssetOwner.asset_id` only on the dedicated private V7-14
registration path. Owner registration/result, PanelAsset, panel attempt,
evidence and accepted composition sources must agree exactly. The server-bound
adapter verifies the complete derivation and request/reservation/configuration
binding before this private handoff. No browser or public request selects IDs.
Legacy V7-04 registration retains `asset-generated-*` and its existing API.
The mode observation's direct ID equality checks remain unchanged.

Exact same-attempt replay verifies ID, provider, media type, digest and bytes;
any different ID for that attempt, cross-attempt ID reuse, missing/corrupt
record, tamper or other binding mismatch fails closed without aliasing,
replacement, repair or migration. An existing mismatched legacy-ID row is not
converted. Preserve current replay/recovery, at-most-once, Page fence, mode
recheck, CAS/EventBus/application proof and no provider fallback/retry rules.
Canonical ID derivations and V7-13 frozen DTOs/authorities remain unchanged.
The implemented owner extension is this private exact-ID registration path,
using the existing registry schema and storage/security machinery. V7-04
transport/security/configuration, generic registration contracts and I02
behavior remain outside the follow-up scope.

### Implemented exact Slice 1 implementation allowlist: six files

The six implementation/test files below were delivered in PR #65 together
with the three approved docs/spec amendment files. The source head was
`5948562b89bb9fef1823800dc6365578c14e48a4`; squash merge commit was
`aa89590498bc145e34db5cc77e1f83008df2e9d3`.

1. `src/manga_director/production/next_generation_local_durable_asset_owner.py`
   - Added the private V7-14 exact-ID path; preserved legacy registration,
     existing persistence/security checks and schema, and rejected conflicting
     replay.
2. `src/manga_director/workflow/localfile_comfyui_panel_provider.py`
   - Route only V7-14's verified canonical panel ID to that private owner path;
     require the returned owner ID to equal the derived ID before acceptance.
3. `tests/test_next_generation_local_durable_asset_owner.py`
   - Cover exact-ID registration/readback/replay, same-attempt different-ID and
     cross-attempt collision rejection, tamper/missing bytes, and unchanged
     legacy `asset-generated-*` behavior.
4. `tests/test_localfile_comfyui_panel_provider.py`
   - Cover canonical derived ID == owner ID == panel/evidence ID, ID mismatch
     rejection, and unchanged prepare/start/submit and no fallback boundaries.
5. `src/manga_director/workflow/localfile_panel_aware_generation_activation.py`
   - Complete only the existing private Slice 1 composition within this amended
     contract; preserve real owner/mode observation and application authorities.
6. `tests/test_localfile_panel_aware_generation_activation.py`
   - Prove success through real owner registration and real final mode recheck
     to Page application; cover mismatches without Page/EventBus/ledger mutation,
     exact RESERVED reuse and uncertain-start recovery using fake transport.

These were the complete implementation files, not six additional files.
No edit to the generic ComfyUI output-registration adapter, asset registration
DTO/protocol, mode observation, repository/CAS, V7-13/V7-14 orchestrator,
converter, public exports, API/Web or configuration is included. If safe reuse
of the existing registration/security machinery requires another file or a
frozen-contract change, STOP and seek a revised design/allowlist. Do not weaken
mode equality or introduce an alias mapping to stay inside this list.

### Slice 1 completion evidence

- PR #65 merged to `v7-dev`; PR-head required checks passed 24/24 before merge.
- Focused tests: 54 passed / 3 skipped.
- Authority regression: 114 passed / 2 skipped.
- V6 LTS regression: 99 passed.
- Full pytest: 3464 passed / 25 skipped.
- GPT-6.1 Sol High independent review: P0/P1/P2/OTHER = 0/0/0/0.
- Source branch `docs/v7-15-planning-rfc` was retained.
- Post-merge CI run #40650264745 passed 10/10; CodeQL run #40650264438 passed
  3/3.

At the time of this Slice 1 completion record, Slice 2 (dedicated HTTP route)
was implemented locally under its separately approved seven-file allowlist;
its full local verification and independent review were pending. It is wired
only for the concrete LocalFile repository, preserves generic `/generate`, and
does not add authentication. Slice 3 (Web activation) remained unimplemented
and unapproved at that historical point. Remote/public deployment,
live ComfyUI, I02, `main`, release/publication, dependency/lockfile,
schema/migration, branch deletion, and package publication remain unperformed
and unauthorized.
