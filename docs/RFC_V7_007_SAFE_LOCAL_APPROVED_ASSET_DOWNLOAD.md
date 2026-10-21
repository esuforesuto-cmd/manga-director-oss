# RFC-V7-007: Safe Local Approved Asset Download

- Status: Design approved; V7-09 implementation complete and verified on `v7-dev`
- Implementation evidence: PR #39 final head
  `28f5cc0b10feb4d88f8d35d0c7ffd0b75d4fbc8f` merged into `v7-dev` at
  `547ab20bf2d92083bc800cf294087cf3ddf4efcb`; pre-merge checks passed 24/24,
  post-merge checks passed 13/13 with CodeQL 3/3, and independent review
  reported P0/P1/P2 = 0/0/0.
- Target line: v7.0 Discovery (Post-LTS)
- Roadmap item: V7-09 Safe Local Approved Asset Download
- Delivery scope: docs-only design
- Decision owner: an explicit local human operator

## Decision boundary

This RFC freezes the smallest loopback-only download design that lets a local
human save the exact V7-07 PNG for one Page only after the existing workflow
has persisted that Page as `Approved` with explicit human approval evidence.

The caller supplies only Project ID and Page number in a fixed local route. The
server resolves the authoritative Page, proves its terminal approval state and
existing approval artifact, reuses the V7-07 Page-to-generation-to-owner proof,
and returns the same safely leased bytes as one attachment response.

The download is not export readiness, packaging, publication, distribution,
or approval. It creates no server-side file, record, archive, metadata,
manifest, audit entry, or browser-derived evidence. It does not make the
transient V7-08 advisory result an approval prerequisite and does not reopen,
repeat, replace, or strengthen the existing approval transition.

This RFC itself adds no endpoint, Web control, source code, test, DTO, public
Python export, persistence field, schema, dependency, or runtime behavior. It
authorizes none.

## Problem

V7-07 can safely present the exact registered PNG bound to a `Generated`,
`QualityChecked`, or `Approved` Page. V7-08 lets a local human submit a
transient visual judgment and receive advisory approval readiness. The
existing approval action remains the sole path from `QualityChecked` to
`Approved`.

After approval, the local Web UI still offers no explicit bounded download
control. Treating artifact metadata as a path or URL would give the browser a
second storage authority. Reopening the registered file by path after V7-07
verification would lose the same-opened-bytes guarantee. Reusing generic
Project export, v5.6 Export Engine planning, or caller-selected filenames would
also conflate one approved PNG download with packaging or publication.

A frozen design is therefore required before implementation so the first
download surface remains a narrow local delivery of already-approved exact
bytes rather than a general export, file-serving, workflow, or publishing
capability.

## Planning summary

- **Title:** V7-09 Safe Local Approved Asset Download
- **Objective:** Download the exact verified PNG already bound to one
  explicitly approved Page through a fail-closed loopback-only attachment.
- **Scope:** One existing LocalFile Project, one existing `Approved` Page, its
  existing approval artifact and terminal workflow history, the one V7-07
  generated-asset proof, and one binary response.
- **Inputs:** Route-supplied Project ID and positive Page number only.
- **Outputs:** The same safely leased PNG bytes with a fixed server-derived
  attachment filename and non-cacheable headers, or one redacted failure.
- **Dependencies:** Completed V7-07 exact asset presentation, completed V7-08
  local visual-review surface, the existing explicit approval transition, and
  the existing LocalFile exact-file lease.
- **Estimated complexity:** Medium for a separately approved implementation;
  Low for this docs-only design.
- **Architecture notes:** One private Application read service composes the
  authoritative Page approval proof with the existing V7-07 private asset
  proof. HTTP remains a presentation adapter, and Web constructs only the
  fixed Project-and-Page route.

## Goals

- Require the existing persisted `Approved` state and explicit approval
  artifact before any attachment response.
- Bind the response to the exact logical generated asset already stored on the
  approved Page.
- Reuse the V7-07 ledger, generation evidence, owner registry, containment,
  digest, byte-limit, strict-PNG, and same-opened-bytes protections.
- Keep the download explicit and user-initiated; rendering or refreshing the
  Page must not start it.
- Derive a bounded ASCII filename only from the validated positive Page number.
- Require server-side evidence that the navigation came from an explicit user
  activation in the existing allowed local Web UI.
- Preserve every workflow, quality, approval, Provider, persistence, public
  API, and v5/v6 compatibility boundary.
- Fail closed when approval or asset authority is missing, ambiguous, stale,
  unsafe, corrupt, or inconsistent.

## Non-goals

- print, Web, eBook, PDF, ZIP, archive, release-bundle, or project export;
- publishing, upload, distribution, sharing, email, notification, or remote
  delivery;
- arbitrary file serving, directory browsing, caller-selected filenames,
  batch or chapter download, multiple assets, thumbnails, conversion,
  transcoding, resizing, metadata extraction, or image editing;
- accepting asset ID, attempt ID, Provider reference, digest, path, storage
  name, root, URI, URL, format, profile, filename, disposition, or range from
  the caller;
- using Project title, Page metadata, approval identity, reviewer identity, or
  artifact metadata in the download filename;
- changing or invoking V7-06 readiness, V7-08 assessment, quality execution,
  approval execution, `StateMachine`, or `WorkflowEngine`;
- recording download history, access analytics, audit evidence, review
  evidence, readiness, or approval evidence;
- creating a server-side copy, temporary file, cache, directory, sidecar,
  registry row, ledger row, evidence row, or database;
- adding CLI, MCP, SDK, Plugin, public Python, remote API, LAN, wildcard,
  authentication, authorization, or role-management surfaces;
- changing Repository, Page, registry, ledger, evidence, or approval schemas;
- invoking v5.6 Export Engine or claiming commercial-delivery readiness;
- Provider construction or calls, generation, regeneration, retry, fallback,
  or Provider switching;
- I02 or use of I02 authority, state, contracts, persistence, or recovery;
- dependency, lockfile, package metadata, version, release, tag, publication,
  Settings, `main`, force-push, history-rewrite, or branch-deletion changes.

## Source contracts

The future download composes existing authorities without replacing them:

- the LocalFile Project aggregate remains authoritative for the exact Page,
  its `Approved` state, immutable logical image descriptor, approval artifact,
  and workflow history;
- the existing explicit approval action and `StateMachine` remain the sole
  authority for reaching `Approved`;
- V7-08 remains transient and advisory; no V7-08 request or result is read as
  persisted approval evidence;
- the V7-07 private proof remains authoritative for Page/attempt/output/
  provenance correlation and retains the exact-file lease;
- `LocalDurableAssetOwner` remains authoritative for the owner root, registry,
  containment, file identity, registered size and digest, and safe lease;
- the strict PNG validator remains authoritative only for PNG container
  structure, not visual quality or approval;
- a private Application read service may coordinate these proofs but acquires
  no workflow, storage, approval, export, or publication authority; and
- the loopback HTTP and Web layers remain presentation adapters.

No Page field, approval value, history entry, ledger binding, registry row,
path, URL, filename, or caller assertion independently authorizes a response.
All required facts must agree.

## Frozen architecture

### Read-only resolution flow

The bounded future flow is:

~~~text
explicit local click
        |
        v
loopback GET with Project ID and Page number only
        |
        v
private approved-asset download Application service
        |
        v
authoritative LocalFile Project -> exact persisted Page
        |
        v
Approved state + exact approval artifact + terminal workflow history
        |
        v
Page logical output_asset_id
        |
        v
existing V7-07 private proof
  -> applied workflow ledger binding
  -> exact generation evidence and provenance
  -> LocalDurableAssetOwner registry
  -> contained ordinary file under the retained safe lease
  -> size + SHA-256 + strict PNG on the same opened bytes
        |
        v
200 image/png attachment with a fixed Page-number filename
~~~

Every step is read-only. A missing or conflicting step ends the request before
any bytes are returned. The implementation must not select the newest output,
scan for a candidate, fall back to presentation metadata, or reopen a path
after verification.

### Route and caller-input boundary

The candidate first-slice route is exactly one additive loopback operation
equivalent to:

~~~text
GET /projects/{project_id}/pages/{page_number}/approved-asset-download
~~~

The only caller-selected values are the existing Project route identifier and
positive Page number. The request has no JSON or form body and no query
parameters.

Before integer conversion or repository access, the raw Page-number segment
must match `^[1-9][0-9]{0,9}$` and its numeric value must be no greater than
`2147483647`. This is a route-local admission bound only; it does not change
the existing Page model or public contract.

The operation rejects:

- any request body or transfer encoding;
- query parameters;
- requests containing any of `Range`, `If-Range`, `If-Match`,
  `If-None-Match`, `If-Modified-Since`, or `If-Unmodified-Since`;
- asset, attempt, Provider, digest, storage, path, root, URL, format, profile,
  filename, or disposition selection; and
- malformed, empty, path-shaped, URL-shaped, traversal-like, or otherwise
  invalid route identity.

The route must not redirect. It must not accept a generic file path, asset
identifier, or signed token as an alternate route.

### Browser-initiated admission boundary

Before repository or lease access, the server must require all of the
following browser-generated evidence for this route:

- exactly one syntactically valid `Referer` whose parsed origin exactly matches
  an entry in the existing local Web-origin allowlist;
- `Sec-Fetch-Mode: navigate`;
- `Sec-Fetch-Dest: document`; and
- `Sec-Fetch-User: ?1`.

An absent, duplicate, malformed, or mismatched value fails closed with the
generic validation response. `Origin`, query parameters, caller tokens, or
custom headers are not substitutes. `Sec-Fetch-Site` is not an admission
condition because an allowed local Web origin and the loopback API may use
different loopback host spellings. Direct address-bar requests and non-browser
clients without this evidence therefore fail closed; the first slice is
available only through its local Web control.

These headers are admission evidence only. They do not select an asset, create
authority, get persisted or logged by this feature, or appear in responses.

### Approval proof

Download eligibility requires all of the following:

- the authoritative Page exists and is exactly `Approved`;
- the Page approval artifact is a closed mapping containing only one non-empty
  `approved_by` string produced by the existing approval action;
- the final workflow-history entry is the canonical transition from
  `QualityChecked` to `Approved` with step `Approved`;
- there is exactly one canonical Generated transition for the current Page;
- the Page image remains the closed logical descriptor with only
  `artifact_kind=logical_output_asset` and one `output_asset_id`; and
- that output ID passes the complete V7-07 proof for the same Project and Page.

The approver identity is evidence only. It is never returned, logged, copied
into a filename, compared with V7-08 reviewer identity, or used as an access
credential.

`ready` from V7-08 is not required, stored, reconstructed, or inferred. The
existing persisted `Approved` state remains sufficient only because the
existing approval action is already the canonical approval authority.

### Exact-byte and lease boundary

The future service must reuse the V7-07 private proof capability rather than
duplicate ledger, evidence, registry, path, digest, or PNG validation.

- The exact file is opened under the platform-specific safe lease.
- The byte limit, registered SHA-256, media type, and strict PNG validator run
  on the same opened bytes returned to HTTP.
- The file is not reopened by path after validation.
- The lease remains held until response completion or abort and is released
  exactly once through the existing response-cleanup mechanism.
- A platform that cannot provide the existing safe exact-file lease fails
  closed; a weaker portable reopen path is not permitted.
- Range or partial responses are not supported.

V7-07 `present()` behavior and its existing generated-asset route remain
unchanged.

### Read-only server-persistence boundary

The GET opens only existing authoritative state. It must not create, repair,
migrate, checkpoint, vacuum, clean up, or normalize anything.

- Project loading is authoritative and read-only.
- Ledger, generation evidence, and owner registry databases are opened only
  through the existing read-only/query-only paths.
- Missing databases, schema mismatch, unsupported journal mode, corruption,
  duplicates, ambiguity, or unsafe filesystem identity fail closed.
- No directory, sidecar, database, journal, temporary file, manifest, access
  log, cache, or downloaded copy is created.
- Before/after manifests for the server/application-controlled Project,
  sidecars, databases, asset root, and service filesystem state are equivalent
  for success and failure.

The intentional browser-managed destination file and any native browser
download history are outside this server-state invariant. The feature never
selects, reads, writes, records, or persists the browser destination path or
native download history; those effects remain wholly under the browser and
user after the verified response leaves the server.

The HTTP adapter must not handle SQLite, owner roots, paths, storage names,
digests, or direct filesystem reads.

### Response contract

Success returns exactly the verified bytes with:

- `200 OK`;
- `Content-Type: image/png`;
- `Content-Disposition: attachment; filename="page-{page_number}.png"`, where
  the filename is generated only from the route-bounded positive integer Page
  number;
- `Cache-Control: no-store`; and
- `X-Content-Type-Options: nosniff`.

The response must not emit:

- `ETag`, `Last-Modified`, `Location`, `Content-Location`, `Accept-Ranges`, or
  a redirect;
- project title or ID, approval or reviewer identity, artifact or attempt ID,
  Provider reference, digest, path, storage name, root, provenance, registry,
  ledger, or evidence metadata; or
- RFC 5987 caller-derived filenames or any filename sourced from persisted
  free text.

An accurate framework-generated `Content-Length` for the returned verified
bytes is permitted. No cache validator or resumable-download contract is
created.

### Error and redaction contract

Malformed caller input returns one generic validation response. Unavailable,
unapproved, unsafe, corrupt, or inconsistent authoritative state returns the
same generic not-found response.

Errors disclose no distinction among:

- missing Project or Page;
- Page not yet approved, malformed approval, or inconsistent history;
- missing, duplicate, corrupt, stale, or mismatched binding/evidence/registry;
- unsafe file identity, path escape, unsupported platform, oversize, digest
  mismatch, malformed PNG, trailing bytes, or partial read; and
- internal configuration or storage failure.

No error contains raw reviewer or approver text, path, filename, digest,
Provider reference, storage identifier, root, SQL detail, traceback, or
internal exception text. Error responses retain `no-store` and `nosniff`.

### Web boundary

The local Page view may show one explicit download control only when the
existing Page DTO says `Approved` and contains the same closed logical image
descriptor already required by V7-07 rendering.

- The browser constructs the fixed route only from Project ID and Page number.
- It does not read or transmit `output_asset_id`, approval data, path, URL,
  digest, Provider, storage name, filename, or root.
- The control is a user-initiated navigation/download, not an eager fetch,
  blob conversion, data URL, prefetch, image reload, or background request.
- Page load, refresh, navigation, polling, approval, or V7-08 assessment does
  not start a download.
- Download success or failure does not create review evidence, change
  readiness, fill approval, mutate Page state, or alter available actions.
- The UI does not claim print, Web, eBook, archive, package, release, or
  publication readiness.

Server authority remains mandatory even when the UI hides the control.

### Network and origin boundary

- The existing exact local Web-origin CORS allowlist is unchanged.
- CORS is not download authority; the route-specific browser-initiated
  admission boundary above remains mandatory.
- Server binding remains loopback-only.
- No DNS resolution, proxy use, redirect following, HTTP client, Provider,
  remote URL, or outbound request is permitted.
- No LAN, wildcard, cloud, remote, CLI, MCP, SDK, Plugin, or public Python
  download surface is introduced.

### Relationship to export and publication

This first slice is a one-file local attachment only. It does not invoke or
extend `V56ExportEngineService`, Project import/export, packaging, metadata,
release-bundle, archive, or publication services.

The response proves only that the exact approved PNG was safely delivered to
the local browser. It does not prove commercial specifications, rights,
metadata, packaging, archive integrity, publication readiness, or successful
storage by the user. Any broader export or publication capability requires a
separate RFC and explicit authorization.

## State behavior

| Persisted Page state | Download result |
| --- | --- |
| `Draft` through `Generated` | Fail closed; approval is absent. |
| `QualityChecked` | Fail closed; explicit approval is still required. |
| `Approved` with complete matching approval and asset proofs | Return the exact PNG attachment. |
| `Approved` with missing, malformed, duplicate, stale, corrupt, or mismatched evidence | Fail closed with no bytes and no repair. |

V7-09 adds no state, transition, command, rejection state, revocation, or
reapproval behavior.

## Determinism

For the same canonical persisted Page and exact registered bytes, the route,
filename, headers, response bytes, and redacted failure class are identical.

- no current time, random identifier, filesystem enumeration, locale,
  environment value, browser state, DNS, network result, or Provider result
  affects selection;
- the filename is a fixed ASCII function of the validated Page number; and
- repeated requests perform the same full read-only proof and accumulate no
  state.

## Failure and recovery semantics

Download is fail-closed and read-only.

- invalid caller input is rejected before authoritative asset access;
- an unapproved or inconsistent Page returns no bytes;
- missing, unsafe, duplicate, ambiguous, corrupt, stale, or mismatched proof
  returns no bytes;
- response abort releases the lease and creates no retry or recovery record;
  and
- no failure retries, chooses a fallback, repairs, re-registers, regenerates,
  reapproves, revokes, transitions, publishes, or notifies.

Recovery consists only of correcting authoritative state through a separately
authorized existing workflow and making a new explicit request. This RFC adds
no repair or recovery command.

## Public contract compatibility

The separately approved V7-09 implementation added one loopback binary GET and
one Web-only download control. All existing JSON DTOs and routes remain unchanged.
Public Python imports and exports remain unchanged.

The design preserves CLI, MCP, SDK, Plugin, Repository, LocalFile, Provider,
generation, quality, visual review, approval, StateMachine, WorkflowEngine,
Project import/export, v5, v6, and public API compatibility. No migration is
required.

Any implementation need for an existing DTO change, public Python export,
StateMachine or WorkflowEngine change, persistence field or schema,
dependency, remote surface, approval coupling, V7-08 persistence, general
export capability, or I02 authority is a scope expansion and must stop for
separate authorization.

## Dependency, migration, and rollback policy

The completed V7-09 implementation used the existing HTTP/Web stack and
existing PNG and exact-file validation, with no runtime or development
dependency, optional extra, lockfile, package metadata, workflow configuration,
or build change. Any future need for these is a scope expansion.

No migration is required. Existing Projects, Pages, approvals, assets,
registries, ledger bindings, generation evidence, and review behavior remain
unchanged.

Planning rollback is to revert this RFC and its matching V7-09 roadmap entry.
Operational rollback for a separately approved implementation is to remove
only the additive route, Web control, private Application read service, and
private composition attachment while leaving Page state and all persisted
evidence untouched.

## Validation plan

This docs-only change requires:

- exact two-file allowlist:
  `docs/RFC_V7_007_SAFE_LOCAL_APPROVED_ASSET_DOWNLOAD.md` and
  `docs/ROADMAP_V7.md`;
- local Markdown-link resolution and `git diff --check`;
- confirmation that source, tests, dependencies, lockfiles, workflows,
  package metadata, versions, Settings, and `main` are unchanged;
- architecture, authority, approval-boundary, exact-file security, privacy,
  public-contract, and compatibility review;
- independent read-only review with P0 = 0 and P1 = 0 before merge; and
- required hosted CI, CodeQL, and post-merge verification.

The separately approved V7-09 implementation additionally required:

- an exact implementation allowlist established by read-only preflight;
- positive Page -> approval -> V7-07 proof -> exact bytes correlation on
  `Approved` only;
- browser-admission rejection before repository access for absent or remote
  `Referer`, malformed or mismatched Fetch Metadata, direct address-bar use,
  iframe navigation, preload, or other non-user-activated requests;
- route-boundary cases for `1` and `2147483647`, plus rejection of zero,
  leading zeroes, `2147483648`, more than ten digits, signs, and non-decimal
  text before integer conversion or repository access;
- rejection for all earlier states, malformed approval/history/image,
  legacy/path-shaped artifacts, duplicates, ambiguity, mismatch, missing or
  corrupt ledger/evidence/registry, unsafe file identity, symlink/junction/
  reparse, oversize, digest mismatch, strict-PNG/trailing-data, and partial
  read;
- query, body, `Range`, `If-Range`, `If-Match`, `If-None-Match`,
  `If-Modified-Since`, `If-Unmodified-Since`, path, asset, filename, format,
  profile, URL, Provider, digest, storage, and root selection rejection;
- proof that success, failure, abort, load, refresh, and repeat create or
  repair no server/application-controlled state, using equivalent before/after
  manifests for the Project, sidecars, databases, asset root, and service
  filesystem state;
- confirmation that only a successful user-initiated response may cause the
  browser to create its chosen destination file or native download history,
  and that the feature neither selects nor programmatically reads, writes, or
  persists either;
- exact binary headers, fixed filename, redacted errors, no redirect/cache
  validator, and no internal or approval metadata leak;
- unchanged CORS and loopback binding plus no DNS, proxy, remote fetch, or
  outbound request;
- no Project/Page/approval/review/readiness mutation, no Provider/generation,
  no retry/fallback, no workflow execution/transition, no export engine, and
  no I02 regression;
- V7-07, V7-08, approval, HTTP/Web, LocalFile, generation, v5/v6, Project
  import/export, and public API compatibility regression;
- full pytest, Ruff, mypy, Web lint/typecheck/test/build, browser E2E,
  security/audit/package, Markdown-link, `git diff --check`, and exact
  implementation allowlist; and
- independent read-only review with P0/P1/P2 classification, followed by CI,
  CodeQL, merge, and post-merge verification only when P0/P1 = 0.

Executed results for the completed V7-09 implementation are summarized above
and in `ROADMAP_V7.md`.

## Acceptance criteria

The design was accepted when:

1. V7-09 has exactly one responsibility: explicit local download of the exact
   approved Page PNG;
2. the caller supplies only Project ID and Page number through one fixed GET;
3. the server admits only a bounded Page-number segment and an explicit
   user-activated document navigation from an existing allowed local Web
   origin before repository or lease access;
4. `Approved`, the closed approval artifact, canonical terminal history, and
   the Page logical asset must all agree;
5. the complete V7-07 proof and safe lease are reused without reopening a path
   or duplicating storage validation;
6. only same-opened bytes that pass existing size, SHA-256, media-type, and
   strict-PNG checks are returned;
7. the attachment filename is fixed from Page number and no persisted or
   caller free text reaches headers;
8. load, refresh, retry, abort, success, and failure create or repair no
   server/application-controlled state; a successful user-initiated response
   may be saved only by the browser without the feature selecting or
   programmatically handling its destination path or native download history;
9. V7-08 readiness remains transient, advisory, and independent from approval
   and download;
10. no export-readiness, packaging, archive, publishing, remote, Provider,
   workflow, persistence, public-contract, dependency, schema, or I02 surface
   is added;
11. the docs-only diff stays within the exact two-file allowlist; and
12. independent review, required CI, CodeQL, and post-merge checks reported no
    blocking issue for the completed V7-09 implementation (see evidence above).

## Authorization gate

At acceptance, RFC-V7-007 authorized only this docs-only design record and the
matching V7-09 roadmap update. The implementation was separately approved and
completed as PR #39 (see evidence above); that authorization is exhausted. This
RFC does not authorize follow-up implementation, publication, approval
changes, Page mutation, review persistence beyond the completed scope, Provider
calls, live generation, I02, dependencies, `main`, versioning, release, tag,
Settings, branch deletion, force push, or history rewriting.

Any future implementation requires a new exact allowlist, explicit
implementation authorization, applicable security and compatibility review,
and executed quality gates. If implementation requires an existing public DTO
change, public Python export, StateMachine or WorkflowEngine change,
persistence or schema change, dependency, remote surface, approval coupling,
general export behavior, or I02 authority, it is outside this RFC and must
stop.
