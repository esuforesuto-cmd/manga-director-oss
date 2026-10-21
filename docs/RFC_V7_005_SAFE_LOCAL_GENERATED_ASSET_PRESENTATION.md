# RFC-V7-005: Safe Local Generated Asset Presentation

- Status: Design approved; V7-07 implementation complete and verified on `v7-dev`
- Implementation evidence: PR #33 final head `d470dc4ddc5be9a33428fc39a9979262fc5578ba`
  merged into `v7-dev` at `9aad271fd8ff66d7516e2f066f55d2a0d62d4fbf`; post-merge
  checks passed 13/13, CodeQL passed 3/3, and independent review reported
  P0/P1/P2 = 0/0/0.
- Target line: v7.0 Discovery (Post-LTS)
- Roadmap item: V7-07 Safe Local Generated Asset Presentation
- Delivery scope: docs-only design
- Decision owner: an explicit local human reviewer

## Decision boundary

This RFC freezes the smallest read-only presentation design that lets the
existing loopback Web UI display the exact registered PNG already bound to one
existing Page.

The presentation input is only the Page identity carried by the local route.
The caller cannot supply an asset identifier, filesystem path, storage name,
URL, Provider reference, digest, or alternate root. The server derives the
Page's persisted logical generated-asset reference, proves its durable
generation binding, resolves the matching `LocalDurableAssetOwner` registry
row, and revalidates the exact registered bytes before returning them.

The bounded future transport is one loopback-only `GET` response with
`Content-Type: image/png` and `Cache-Control: no-store`. It is presentation
only. It performs no mutation, Provider call, generation, workflow execution,
state transition, approval, human-review recording, or I02 operation.

This RFC itself adds no implementation, endpoint, DTO, public Python export,
persistence format, dependency, or Web behavior. It authorizes none.

## Problem

V7-03 through V7-05 can durably register validated generated PNG bytes, and
V7-06 can correlate logical generation evidence with an explicit human visual
judgment and advisory approval readiness. The current local HTTP and Web
delivery surfaces expose Page metadata and artifacts as JSON, but they do not
provide a safe byte-presentation path for the human reviewer to inspect the
exact registered output.

Allowing a caller to submit a path, storage name, asset identifier, or URL
would create a second filesystem or network authority. Serving a file from a
Page reference without rechecking the durable binding, registry, digest, and
PNG structure would permit stale, replaced, corrupt, or mismatched bytes to be
shown as review evidence.

A frozen design is therefore required before implementation so local image
presentation cannot become arbitrary file serving, remote fetching, workflow
execution, or an approval shortcut.

## Planning summary

- **Title:** V7-07 Safe Local Generated Asset Presentation
- **Objective:** Present the exact registered PNG already bound to one
  existing Page through a fail-closed, loopback-only, read-only path.
- **Scope:** One existing Project, one existing Page, its one persisted logical
  generated-asset reference, the matching durable generation binding, one
  exact `LocalDurableAssetOwner` registry row, and one verified PNG response.
- **Inputs:** Route-supplied Project and Page identity plus server-owned
  persisted evidence. No caller-selected file, asset, Provider, digest, or URL.
- **Outputs:** The verified PNG bytes with fixed safe response headers, or a
  redacted failure with no storage disclosure.
- **Dependencies:** Completed V7-01 local HTTP delivery, the verified LocalFile
  generation/registration chain, V7-05 hardening, and completed V7-06 logical
  review binding on `v7-dev`.
- **Estimated complexity:** Medium for a separately approved implementation;
  Low for this docs-only design.
- **Architecture notes:** Additive local presentation composition only. The
  HTTP adapter delegates to a transport-neutral private Application read
  service, the repository identifies the Page, the durable binding identifies
  the exact logical output, `LocalDurableAssetOwner` remains the storage
  authority, and the HTTP layer returns only verified bytes.

## Goals

- Bind every successful response to one exact existing Page and its persisted
  logical generated asset.
- Resolve bytes only through server-owned durable evidence and the
  `LocalDurableAssetOwner` registry.
- Revalidate registry integrity, Page/attempt/asset binding, media type,
  containment, byte limit, SHA-256 digest, and strict PNG structure on every
  presentation.
- Return the verified bytes through the existing loopback-only HTTP server
  without disclosing a path or storage name.
- Preserve all workflow, approval, Provider, persistence, and public
  compatibility authorities.
- Fail closed and deterministically when any identity, integrity, or safety
  fact is absent, ambiguous, duplicated, stale, or conflicting.

## Non-goals

- arbitrary file serving, directory browsing, download management, thumbnails,
  conversion, transcoding, resizing, metadata extraction, or image editing;
- accepting an asset ID, attempt ID, Provider reference, digest, storage name,
  filesystem path, URI, URL, alternate root, query-selected output, or request
  body from the caller;
- remote, LAN, wildcard, cloud, DNS-name, proxy, redirect, or any origin beyond
  the existing explicit local Web-origin allowlist;
- fetching Provider, ComfyUI, OpenAI, Marketplace, HTTP, HTTPS, data, file, or
  other URL content;
- generation, regeneration, retry, replacement, fallback, Provider selection,
  or Provider switching;
- Project, Page, asset, registry, evidence, review, readiness, or approval
  mutation or persistence;
- workflow execution, state transition, quality execution, approval execution,
  reviewer authentication, authorization, or role management;
- changing `StateMachine`, `WorkflowEngine`, Page states, transition rules,
  generation admission, approval authority, or V7-06 readiness semantics;
- adding a public Python API, CLI command, MCP tool, SDK surface, Plugin
  contract, remote API, or general-purpose asset endpoint;
- I02 or use of any I02 authority, commitment, verifier, persistence, contract,
  or implementation;
- dependency, lockfile, package metadata, version, release, tag, publication,
  Settings, `main`, force-push, history-rewrite, or branch-deletion changes.

## Source contracts

The future presentation composes existing authorities without replacing them:

- the repository remains authoritative for locating the existing Project and
  Page and reading the Page's persisted `Generated` logical artifact;
- the existing durable generated-application evidence remains authoritative
  for the one Page/attempt/output/provenance relationship;
- a transport-neutral private Application read service coordinates the
  repository read, durable-binding proof, and owner read without acquiring any
  of their authorities;
- `LocalDurableAssetOwner` remains authoritative for the private owner root,
  registry, storage-name derivation, containment, and registered digest;
- the strict PNG validator remains authoritative only for PNG container
  structure and is not a visual-quality judgment;
- the HTTP adapter remains a loopback Presentation adapter and does not become
  repository, workflow, or filesystem authority; and
- V7-06 remains the advisory human-review/readiness boundary and receives no
  automatic review evidence from displaying bytes.

No registry row, ledger entry, Provider descriptor, URL, path-like metadata,
or HTTP input can independently authorize a response. All required bindings
must agree.

## Frozen architecture

### Read-only resolution flow

The future bounded flow is:

~~~text
loopback GET with Project ID and Page number only
        |
        v
private Application presentation read service
        |
        v
existing repository -> exact persisted Page
        |
        v
Page Generated artifact -> one logical output_asset_id
        |
        v
durable generation binding -> exact Page / attempt / asset / provenance
        |
        v
LocalDurableAssetOwner registry -> exact media type / digest / storage record
        |
        v
contained ordinary file opened under the owner root
        |
        v
size + SHA-256 + strict PNG revalidation on the exact opened bytes
        |
        v
200 image/png with Cache-Control: no-store
~~~

Every step is read-only. A missing or conflicting step ends the request before
any bytes are returned. The implementation must not scan for a newest asset,
choose among attempts, fall back to another Page or Provider, or infer a
replacement output.

### Route and caller-input boundary

The candidate first-slice route is a single additive local presentation route
equivalent to:

`GET /projects/{project_id}/pages/{page_number}/generated-asset`

Only the existing validated Project identifier and positive Page number are
accepted. The route has no request body and no query parameter. In particular,
it does not accept `path`, `filename`, `storage_name`, `asset_id`, `attempt_id`,
`provider_reference`, `digest`, `url`, `root`, or a content-negotiation value
that changes the selected bytes.

The route is hosted only by the existing workflow API bound to
`127.0.0.1`. The implementation must not add a host override, remote bind,
second listener, remote origin, or wider CORS allowance. Other HTTP methods,
range selection, redirects, conditional cache validators, directory indexes,
and multi-asset responses are outside the first slice.

This route is the only new delivery behavior contemplated by this design. It
does not convert the local adapter into an internet-facing or general public
asset API, and it does not alter any existing route or DTO.

### Exact Page and registered-asset binding

A response is eligible only when all of the following identify the same
existing output:

1. the route identifies exactly one persisted Project and Page;
2. the Page has exactly one canonical `Generated` artifact with
   `artifact_kind` equal to `logical_output_asset` and one logical
   `output_asset_id`;
3. the durable generation/application evidence binds that Project and Page to
   exactly one attempt, Provider reference, output asset, provenance identity,
   media type, digest, and expected byte length where already recorded;
4. one exact owner-registry row exists for the same asset, attempt, Provider
   reference, `image/png` media type, and digest; and
5. one exact contained ordinary file matches the row and all persisted facts.

The handler must not accept a caller-selected asset ID, use registry order,
filesystem order, modification time, or a "latest" rule. Duplicate rows,
missing evidence, legacy path-shaped artifacts, multiple candidate outputs,
unsupported Page artifacts, or any mismatch fail closed.

Presentation may occur for a Page that has progressed beyond `Generated` only
when its immutable `Generated` logical artifact and complete durable binding
remain intact. Presentation neither requires nor produces `QualityChecked`, a
V7-06 readiness result, or `Approved`.

### LocalDurableAssetOwner read authority

The completed V7-07 implementation added or composed a narrowly private,
read-only presentation capability around the existing `LocalDurableAssetOwner`.
The HTTP
adapter must not inspect SQLite, construct a storage path, or open a file
itself. It delegates to the private Application read service, which coordinates
the existing authorities without reimplementing their validation.

The owner-side read must:

- use only an already-existing owner root and registry and must not create
  directories, initialize a registry, repair schema, or register an asset on a
  read request;
- open the registry in read-only/query-only mode and require the exact expected
  schema and one matching row;
- validate the registry-owned storage name internally without returning it;
- keep configured-root containment and ordinary-file checks, rejecting
  symbolic links, junctions, reparse points, devices, directories, or path
  escape;
- enforce the existing 25 MB registered-byte limit;
- hash the exact opened bytes and compare them with the registered SHA-256
  digest using the existing fail-closed integrity boundary;
- run strict PNG structural validation, including signature, chunk ordering,
  CRC, required `IHDR`/`IDAT`/`IEND`, and rejection of trailing or malformed
  data; and
- return or stream only the same opened bytes that passed validation, retaining
  the protective lease until the response is complete.

No later path reopen may substitute different bytes after validation. An
implementation must preserve the platform-specific owner-root and file
identity protections already required by the supported LocalFile runtime. A
platform without an equivalent safe exact-file lease fails closed rather than
weakening the boundary.

This capability is presentation-specific and independent of I02. It must not
consume, mint, import, or emulate I02 commitments or recovery authority.

### HTTP response contract

A successful response contains only the verified PNG bytes and these fixed
presentation facts:

- status `200`;
- `Content-Type: image/png`;
- `Cache-Control: no-store`; and
- `X-Content-Type-Options: nosniff`.

The response must not include a filesystem path, owner root, registry path,
storage name, Provider filename, source URL, digest, attempt ID, Provider
reference, secret, arbitrary metadata, `ETag`, `Last-Modified`, redirect
`Location`, or caller-derived download filename.

Failures use the existing redacted HTTP error boundary or an equally narrow
binary-route error mapping. Invalid route input, missing Project/Page/output,
binding mismatch, corrupt registry, unsafe file identity, size failure, digest
mismatch, malformed PNG, or read failure returns no image bytes and no storage
detail. Error handling must not turn an integrity failure into a different
asset lookup.

### Browser presentation boundary

The future Web UI may render the loopback API route for the selected Page only
from an origin already present in the existing explicit local Web-origin CORS
allowlist. It must not receive or construct a local path, storage name,
Provider URL, remote URL, or data URL from Page metadata. It must not fetch an
image directly from ComfyUI, OpenAI, another Provider, or a filesystem scheme.

Displaying the image is not human-review evidence. The browser must not create
or persist a V7-06 judgment, readiness result, quality result, or approval as a
side effect of load, success, failure, refresh, or navigation.

## Network and transport security

- The existing workflow API remains bound only to the IPv4 loopback literal
  `127.0.0.1`; no remote, LAN, wildcard, unspecified, or cloud listener is
  introduced.
- The route performs no outbound request and accepts no URL. DNS resolution,
  proxy routing, redirect following, Provider fetches, and same-name remote
  fallback are prohibited.
- The existing local Web-origin allowlist is not widened. A future
  implementation must preserve the current local delivery boundary and test
  that no remote origin is added.
- The endpoint never emits a redirect. Missing or unsafe content fails with a
  redacted error rather than a `Location` response.
- `Cache-Control: no-store` is mandatory on successful image responses and
  applicable error responses so review bytes and path-sensitive failures are
  not retained by shared or browser caches.
- Range and conditional requests are not part of the first slice. The server
  returns the one complete verified PNG or no image bytes.

Loopback limits network reachability; it does not authenticate local users.
Authentication, multi-user access control, remote collaboration, and hostile
same-host isolation require a separate design and are not implied by this RFC.

## Mutation and authority exclusions

The presentation request must not:

- save or update a Project or Page;
- create, update, repair, vacuum, or migrate a registry or ledger;
- register, copy, rename, replace, delete, quarantine, or touch an asset;
- call `WorkflowEngine`, execute an Agent, request a StateMachine transition,
  or change Page state;
- construct, select, preflight, or invoke a Provider;
- generate, retry, regenerate, reconcile, or recover an output;
- run quality review, Visual Continuity QA, or V7-06 readiness;
- record reviewer identity, judgment, rationale, access history, approval
  evidence, or review persistence;
- approve, reject, reopen, revoke, or otherwise alter approval state; or
- access I02 code, state, evidence, commitments, verifiers, or recovery paths.

Observability must remain bounded to redacted request outcome information and
must not log raw bytes, paths, storage names, digests, Provider responses, or
secrets. Adding an access ledger or analytics persistence is outside scope.

## Failure and recovery semantics

Presentation failure is read-only and fail-closed.

- Invalid or ambiguous Page/output binding returns no image.
- Missing, duplicated, unavailable, corrupt, or mismatched registry evidence
  returns no image.
- An unsafe file identity, path escape, unsupported media type, size failure,
  digest mismatch, malformed PNG, partial read, or response failure returns no
  alternate image.
- No failure triggers mutation, repair, re-registration, generation, retry,
  fallback, Provider switching, workflow execution, notification, review
  persistence, or approval.
- Retrying the same safe `GET` may repeat the complete read-only validation; it
  never consumes generation or approval authority.

Operational recovery is limited to correcting the underlying persisted state
through a separately authorized workflow and then making a new read-only
request. This RFC creates no repair or recovery command.

## Public contract compatibility

This docs-only design changes no current contract. The completed V7-07
implementation was limited to the explicitly bounded additive loopback binary
`GET` and private presentation composition. It preserved:

- all current Python imports, exports, signatures, return shapes, and exception
  behavior;
- existing CLI commands and defaults, MCP tools and schemas, SDK and Plugin
  contracts;
- all existing HTTP routes, JSON DTOs, status behavior, CORS allowlist, and Web
  workflow behavior;
- Repository and LocalFile persisted formats, registry schema, generation
  evidence, and existing Project readability;
- `StateMachine`, `WorkflowEngine`, Page states, transition rules, one-Page
  execution, and storyboard-before-generation;
- mock defaults, OpenAI and ComfyUI behavior, Provider neutrality, and
  credential-free/no-network default operation;
- `QualityChecked` before explicit human approval and all V7-06 advisory
  readiness boundaries; and
- v5/v6 compatibility and the unchanged `main` LTS line.

No existing endpoint changes meaning, and no new Python, CLI, MCP, SDK, Plugin,
or remote public API was authorized. At design time, V7-07 was blocked pending
a separate implementation decision. The bounded implementation was
subsequently approved and completed by PR #33 (see evidence above). Any future
scope requiring a persistence migration, dependency, public export, existing
DTO change, StateMachine change, WorkflowEngine change, Provider change, or I02
still requires a separate decision.

## Dependency, migration, and rollback policy

The completed V7-07 implementation used the standard library and
already-declared local HTTP/Web capabilities, with no runtime or development
dependency, optional extra, lockfile, package metadata, or build change. Any
future need for a new image decoder, database package, transport client, or
other dependency is a scope expansion.

No migration is required. Existing Projects, Pages, generated artifacts,
owner registries, generation evidence, review evidence, and approvals remain
unchanged.

Planning rollback is to revert this RFC and the matching V7-07 roadmap entry.
Operational rollback for a separately approved implementation is to remove or
disable only the additive presentation route and UI rendering while leaving
registered assets and all persisted evidence untouched. Rollback must not
delete assets, rewrite registries, change Page state, or revoke approval.

## Validation plan

This docs-only design change requires:

- exact changed-file review proving only this RFC and `docs/ROADMAP_V7.md`
  changed;
- local Markdown-link resolution;
- `git diff --check`;
- confirmation that source, tests, dependencies, lockfiles, workflows,
  package metadata, versions, settings, and `main` are unchanged;
- architecture, authority, security, compatibility, and scope review;
- independent read-only review with P0 = 0 and P1 = 0 before merge; and
- required hosted CI and CodeQL checks for the final commit.

The separately approved V7-07 implementation additionally required:

- an exact implementation allowlist before modification;
- positive tests proving Page → durable binding → registry → exact-byte
  correlation for Generated, QualityChecked, and Approved Pages where valid;
- rejection tests for caller asset/path/URL selection, query/body input,
  legacy artifacts, duplicates, ambiguity, and every binding mismatch;
- read-only registry/schema tests and proof that missing state is not created
  or repaired by `GET`;
- containment, symlink/junction/reparse, ordinary-file, root-identity,
  replacement-race, byte-limit, digest, strict-PNG, trailing-data, and partial
  read tests;
- exact response-header and redacted-error tests, including no path, storage
  name, digest, Provider metadata, redirect, cache validator, or filename leak;
- loopback-only, unchanged CORS, no-DNS, no-proxy, no-redirect, and no-outbound
  network tests;
- no-mutation, no-Provider, no-generation, no-review-persistence, no-approval,
  no-StateMachine, no-WorkflowEngine, and no-I02 regression tests;
- Web rendering tests proving the browser uses only the same local route and
  does not treat display as a human judgment or approval;
- existing Python, HTTP, Web, LocalFile, generation, V7-06, public-contract,
  v5/v6, security/audit, package, and full regression gates; and
- final independent review, CI, CodeQL, exact allowlist, and
  `git diff --check` evidence.

Executed results for the completed V7-07 implementation are summarized above
and in `ROADMAP_V7.md`.

## Acceptance criteria

The design was accepted when reviewers confirmed that it:

1. presents only the exact registered PNG bound to one existing Page;
2. accepts only Project and Page identity and forbids caller-supplied asset,
   attempt, Provider, digest, path, storage name, root, URL, query, or body
   selection;
3. resolves Page → durable generation binding → owner registry → exact bytes
   without scanning, guessing, or selecting a latest output;
4. keeps `LocalDurableAssetOwner` authoritative for registry, storage-name,
   containment, digest, byte-limit, and exact-file handling;
5. revalidates SHA-256 and strict PNG structure on the same opened bytes that
   are returned;
6. defines one loopback-only `GET` returning `image/png` with
   `Cache-Control: no-store` and no path or storage-name disclosure;
7. prohibits remote, DNS, proxy, redirect, Provider, and arbitrary-file
   behavior;
8. is fully read-only and performs no mutation, generation, review
   persistence, readiness, approval, StateMachine, or `WorkflowEngine`
   operation;
9. remains completely independent of I02 and authorizes no dependency,
   persistence, migration, existing public-contract, version, release, or
   `main` change;
10. stays within the exact two-file docs allowlist; and
11. independent review, required CI, CodeQL, and post-merge checks reported no
    P0 or P1 finding for the completed V7-07 implementation (see evidence above).

## Authorization gate

At acceptance, RFC-V7-005 authorized only this docs-only design record and the
matching V7-07 roadmap update. The implementation was separately approved and
completed as PR #33 (see evidence above); that authorization is exhausted. This
RFC does not authorize follow-up implementation, live generation, Provider
use, Project or Page mutation, review persistence beyond the completed scope,
approval, I02, dependencies, `main`, versioning, release, tag, publication,
Settings, branch deletion, force push, or history rewriting.

Any future implementation requires a new exact allowlist, explicit
implementation authorization, applicable security and compatibility review,
and executed quality gates. If implementation requires a third design file,
new dependency, persistence change, existing public contract change,
StateMachine or `WorkflowEngine` change, remote surface, live operation, or
I02 authority, it is outside this RFC and must stop.
