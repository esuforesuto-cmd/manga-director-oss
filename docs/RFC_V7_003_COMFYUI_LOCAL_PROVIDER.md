# RFC-V7-003: ComfyUI Local Provider Delivery

- Status: Design frozen; implementation not authorized
- Target line: v7.0 Discovery (Post-LTS)
- Related roadmap item: V7-04 ComfyUI Local Provider
- Reference Provider: local ComfyUI server
- Default endpoint: `http://127.0.0.1:8188`
- Delivery boundary: CLI-only explicit opt-in candidate

## Decision boundary

The `6.0.x` line remains LTS, and `main` remains the LTS stability line. This
RFC freezes the smallest safe architecture for applying the Provider-neutral
LocalFile durable real-generation boundary completed by V7-03 to a second
reference Provider: a local ComfyUI server.

This RFC and its matching roadmap update are design documents only. They do
not authorize implementation, a live ComfyUI request, a CLI change, a
dependency change, versioning, release, tag, publication, repository settings,
branch deletion, force push, or a change to `main`. Any later implementation
requires a separately approved exact allowlist and validation plan.

I02 remains completely independent and outside this RFC. V7-04 must not use
I02 authority, imports, persistence, contracts, or implementation. If a later
implementation cannot proceed without I02, V7-04 is `BLOCKED` pending separate
approval; its scope must not be widened silently.

## Problem

V7-03 established one explicit, durable, Provider-neutral route from a
CLI-authorized LocalFile generation attempt to one validated PNG and existing
workflow application authority. OpenAI is its first reference Provider. The
repository still has no approved design for applying that boundary to a local
ComfyUI server without weakening at-most-once Provider-start behavior,
trusting ComfyUI-owned filesystem paths, or turning the legacy public
`ComfyUIImageGenerator` stub into a network client.

ComfyUI also accepts workflow graphs and may load third-party custom nodes.
Those inputs can expand execution far beyond prompt-only image generation.
The first slice therefore needs a fixed Manga Director-owned graph, strict
loopback transport, byte-only result handling, and a fail-closed recovery rule
before any implementation can be considered.

## Goals

- Reuse the V7-03 Provider-neutral LocalFile durable attempt and admission
  boundary for one local ComfyUI generation.
- Define ComfyUI as the second reference Provider without making it part of
  the workflow, Domain, StateMachine, or public API contract.
- Keep the first candidate delivery CLI-only, explicitly selected with
  `--real-provider comfyui`, and gated by durable human authorization evidence.
- Limit one admitted attempt to one Page, prompt-only input, and exactly one
  validated PNG.
- Use the local ComfyUI server API through `POST /prompt`, bounded
  `/history/{prompt_id}` polling, and `/view` byte retrieval without requiring
  WebSocket support.
- Prevent automatic duplicate execution when submission or completion is
  ambiguous.
- Preserve existing asset ownership, workflow application, compatibility,
  security, and approval authorities.

## Non-goals

V7-04 first-slice design does not include:

- implementation or any live ComfyUI call;
- changing the legacy public `ComfyUIImageGenerator` deterministic stub;
- remote or LAN endpoints, DNS hostnames, cloud endpoints, proxies, tunnels,
  reverse proxies, wildcard listeners, or ComfyUI `--listen` exposure;
- reference images, image-to-image input, ControlNet input, uploads, or other
  non-prompt input;
- multiple Pages, batch output, multiple selected images, or parallel
  generation;
- background, scheduled, autonomous, or detached generation;
- automatic retry, replacement attempts, Provider fallback, or automatic
  Provider switching;
- user-supplied workflow JSON, arbitrary graph editing, custom nodes,
  third-party node packages, embedded scripts, or node installation;
- bundling ComfyUI, models, checkpoints, custom nodes, or node packages in the
  Manga Director repository or distribution;
- authentication, API keys, credential storage, or secret management for the
  local endpoint;
- HTTP, Web UI, MCP, SDK, Plugin, repository-schema, StateMachine, or public
  API changes;
- dependency or lockfile changes; or
- I02 authority, imports, persistence, contracts, or implementation.

## Frozen architecture

### Provider-neutral composition

The ComfyUI adapter is a private infrastructure transport behind the same
Provider-neutral invocation and LocalFile durable execution composition used
by V7-03. Provider-specific request, workflow, polling, and output metadata
must not enter Domain models, StateMachine transitions, `WorkflowEngine`, HTTP
DTOs, MCP schemas, or existing LocalFile public formats.

```text
CLI explicit opt-in plus durable human authorization evidence
                              |
                              v
Existing WorkflowEngine and LocalFile durable admission/attempt boundary
                              |
                              v
Provider-neutral invocation port
                              |
                              v
Private ComfyUI transport and fixed core-node graph
                              |
                              v
POST /prompt -> bounded GET /history/{prompt_id} -> GET /view bytes
                              |
                              v
Strict PNG and 25 MB validation -> LocalDurableAssetOwner
                              |
                              v
Existing external-generated application and StateMachine authority
```

The design reuses conceptually, without changing their public contracts:

- LocalFile durable admission and attempt identity;
- explicit human execution and workflow authorization evidence;
- the Provider-neutral invocation port and composition boundary;
- non-secret generation evidence;
- `LocalDurableAssetOwner`;
- strict PNG structural validation and the 25 MB registered-byte limit;
- external generated-result application through existing
  `StateMachine`/`WorkflowEngine` authority; and
- the ambiguous-outcome no-retry rule.

A later implementation is expected to need only private ComfyUI pieces:

- a loopback endpoint validator and read-only health preflight;
- a fixed workflow template and validator;
- prompt submission, result polling, and image-fetch transport;
- ComfyUI-private output material; and
- a Provider-private asset-registration adapter, or a minimal
  Provider-neutral generalization if that can be proven compatible.

These component names describe ownership and responsibility, not approved
files, public types, imports, or implementation authority.

### Legacy adapter boundary

The existing public `ComfyUIImageGenerator` remains a deterministic,
non-network stub. It must not acquire endpoint configuration, HTTP calls,
workflow loading, model discovery, filesystem access, credentials, or live
generation behavior. Existing imports, construction, call forms, return
shapes, deterministic behavior, and tests remain unchanged.

Real ComfyUI generation, if later approved, is composed separately through
the LocalFile durable generation route. The legacy stub cannot serve as a
fallback or bypass durable admission, authorization, validation, or recovery.

### CLI-only explicit opt-in

The candidate first slice uses an explicit CLI selection equivalent to
`--real-provider comfyui` together with non-empty human authorization
evidence for the specific attempt. The exact CLI change is not authorized by
this RFC.

`mock` remains the default. OpenAI V7-03 behavior remains unchanged. Starting,
opening, installing, or upgrading Manga Director must not discover or invoke
ComfyUI automatically. Missing, malformed, conflicting, stale, or replayed
authorization or opt-in evidence fails before network access.

## Endpoint and transport safety

The default and only baseline endpoint is `http://127.0.0.1:8188`. A later
implementation must validate the parsed destination before every request and
must fail closed for:

- a non-HTTP scheme;
- credentials or user information embedded in the URL;
- a fragment, unexpected query, or path prefix supplied as endpoint input;
- DNS names, including names that currently resolve to loopback;
- any non-loopback IPv4 or IPv6 literal;
- remote, LAN, cloud, proxy, wildcard, or unspecified addresses;
- redirects of any status code; or
- a response whose effective origin differs from the validated endpoint.

The transport must not honor environment or system proxy routing for ComfyUI
requests. The first slice must not configure, start, expose, or reconfigure a
ComfyUI server and must not support a server launched with remote `--listen`
semantics. Any future endpoint configuration remains constrained to a strict
loopback IP literal and requires its own validated implementation scope.

No API key or secret is expected for the localhost first slice. Adding
authentication, credentials, TLS termination, or remote operation requires a
separate design and authorization.

## Read-only preflight

Before the attempt consumes its Provider-start opportunity, the private
transport must perform bounded read-only checks against the validated
loopback origin. The checks establish that:

- the ComfyUI server is reachable and responds with expected JSON;
- every node type in the fixed graph is available as a core node;
- the selected local checkpoint is available by its exact validated name; and
- no required graph feature depends on a custom node or third-party package.

Preflight must not queue work, install or update nodes, download models,
change server configuration, upload inputs, or mutate Manga Director workflow
state. A failed or malformed preflight fails closed before `POST /prompt`.
Preflight success is not authorization to submit and must not be cached as a
substitute for durable attempt admission.

## Fixed workflow graph policy

The first slice uses a Manga Director-owned, versioned, core-node-only
workflow template. The template fixes node classes, graph connections, output
count, batch size of one, and the single image-producing output. Only narrowly
typed values required for the admitted prompt-only execution may be
substituted, such as the prompt, an approved local checkpoint reference, and
bounded generation parameters.

The implementation must validate the completed graph against an explicit
allowlist before submission. User input must not change node classes, add
nodes, alter edges, supply executable text, choose an output path, or increase
batch/output count.

Arbitrary user workflow JSON, imported workflows, custom nodes, third-party
node packages, dynamic node discovery, embedded scripts, and node-management
operations are unsupported. ComfyUI's own security model treats custom nodes
as arbitrary Python code trusted like other installed software; Manga
Director therefore does not accept them into the V7-04 contract, even if a
user has installed them locally.

## Submission, polling, and result-byte flow

The frozen flow is:

1. Validate CLI opt-in and durable human authorization evidence.
2. Admit and persist one immutable LocalFile attempt for one eligible Page.
3. Validate the endpoint and complete the bounded read-only preflight.
4. Materialize and validate the fixed prompt-only core-node graph.
5. Mark the attempt's single Provider-start opportunity consumed immediately
   before issuing `POST /prompt`.
6. Submit once and require one well-formed `prompt_id` response associated
   with the admitted attempt.
7. Observe only that identifier through bounded, read-only
   `/history/{prompt_id}` polling. WebSocket support is not required.
8. Require one successful history result containing exactly one supported
   image descriptor for the fixed output node.
9. Validate the descriptor as untrusted metadata and fetch bytes only through
   same-origin `/view` with redirects disabled.
10. Validate response status, `Content-Type`, byte count, strict PNG structure,
    and evidence consistency before asset registration.
11. Pass only the validated bytes and non-secret evidence to the existing
    LocalFile asset owner and external-generated application authority.

Safe read-only history polling may repeat within the bounded observation
window for the same `prompt_id`; it must never cause another submission.
Polling must have finite time and response-size bounds. Unexpected JSON,
missing or conflicting identifiers, multiple outputs, execution failure, or
an observation deadline fails closed.

The filename, subfolder, and type returned by ComfyUI are untrusted lookup
metadata for `/view`, not filesystem authority. Manga Director must never
join, open, stat, copy, or otherwise read a ComfyUI output path directly.

## Ambiguous outcome and recovery semantics

`POST /prompt` is the external side-effect start point. Once submission begins,
the attempt has consumed its only Provider-start opportunity.

If timeout, connection loss, process loss, malformed response, missing
`prompt_id`, result-observation failure, or persistence failure leaves it
uncertain whether ComfyUI accepted or completed the request, the attempt fails
closed as `RECOVERY_REQUIRED`. The system must not automatically:

- repeat `POST /prompt`;
- create a replacement attempt;
- submit a different workflow;
- switch to OpenAI, mock, or another Provider; or
- claim that generation did not occur.

A future recovery operation may perform separately authorized read-only
reconciliation against preserved evidence. Any recovery path that can issue a
new external side effect requires a separate design and explicit approval.
This RFC does not create a public recovery API.

## Asset and PNG handling

Only bytes fetched from `/view` may cross the ComfyUI-private boundary. Before
those bytes reach `LocalDurableAssetOwner`, the implementation must:

- reject redirects and an unexpected origin;
- require an expected image response and reject an unexpected
  `Content-Type`;
- enforce the existing maximum of 25 MB while streaming, not only after the
  complete body is buffered;
- require exactly one PNG and apply the existing strict structural PNG
  validation;
- reject truncated, trailing, malformed, unsupported, or multiple selected
  outputs;
- reject unsafe filename, subfolder, type, query, and path metadata; and
- bind non-secret Provider, attempt, prompt, output, digest, and authorization
  evidence consistently.

The LocalFile asset owner remains responsible for safe naming, ownership,
containment, atomic persistence, digest evidence, and registration. ComfyUI
filesystem names and paths never become LocalFile asset paths.

## Public contract compatibility

RFC acceptance changes no public contract. A later implementation must be
additive, private to the approved composition boundary, and preserve:

- v5/v6 Python imports, call forms, return shapes, and exception behavior;
- existing CLI commands and defaults except the separately approved explicit
  opt-in addition;
- MCP tools, schemas, imports, and local stdio behavior;
- HTTP DTOs and Web UI behavior;
- SDK and Plugin contracts;
- `OpenAIImageGenerator` and `ComfyUIImageGenerator` stub behavior;
- OpenAI V7-03 selection, authorization, invocation, and result behavior;
- `mock` as the default and credential-free/no-network operation;
- `StateMachine`, `PageState`, transition rules, and `WorkflowEngine`
  one-Page authority;
- storyboard-before-generation and `QualityChecked`-before-`Approved` with
  explicit human approval;
- existing LocalFile schemas, containment, path safety, and security; and
- all v5/v6/public compatibility guarantees.

No private type or V7-04 implementation detail becomes public merely because
this RFC names its responsibility. Any necessary public-contract,
StateMachine, LocalFile-schema, default, HTTP, Web, MCP, OpenAI, or I02 change
is a scope expansion and blocks V7-04 pending separate approval.

## Dependency and packaging policy

A future implementation must prefer the Python standard library or already
declared runtime dependencies. This RFC authorizes no new dependency,
optional extra, lockfile, package metadata, or build change. If a new
dependency is proven necessary, it requires a separate bounded scope,
dependency and license review, and explicit approval.

ComfyUI, custom nodes, models, and checkpoints remain independently installed
local software and data. Manga Director must not vendor, copy, redistribute,
or package their code or artifacts. The integration communicates with an
external local service, so this design requires no ComfyUI code copy or
license incorporation.

## Security considerations

- Treat the local ComfyUI server as a privileged local service, not as a
  trusted source of paths, filenames, response sizes, media types, or JSON.
- Permit network use only after explicit opt-in, durable admission, human
  authorization validation, endpoint validation, and read-only preflight.
- Use only a validated loopback IP literal; reject DNS, remote hosts,
  redirects, proxies, credentials in URLs, and unsupported schemes.
- Keep all requests on the same validated origin and apply finite connect,
  read, polling, response-size, and total-operation bounds.
- Use only the fixed core-node graph and reject custom or unknown node types.
- Never install, update, or invoke custom nodes through Manga Director.
- Never directly access paths reported by ComfyUI; retrieve bytes through
  `/view` and validate them before LocalFile ownership.
- Preserve non-secret evidence without storing whole Provider responses,
  arbitrary workflow JSON, local filesystem disclosure, or future secrets.
- Prevent duplicate submission across timeout, process loss, refresh,
  restart, concurrency, and ambiguous results.
- Keep default, test, package, and documentation validation paths offline and
  credential free.

The endpoint and custom-node restrictions align with ComfyUI's published
[security policy](https://github.com/Comfy-Org/ComfyUI/blob/master/SECURITY.md),
which describes a localhost-only default and treats custom nodes as arbitrary
trusted Python code. The submission/history/view sequence is based on the
official ComfyUI repository's
[server routes](https://github.com/Comfy-Org/ComfyUI/blob/master/server.py) and
[API example](https://github.com/Comfy-Org/ComfyUI/blob/master/script_examples/basic_api_example.py).

## Migration and rollback

This design requires no migration. Existing Projects, mock workflows, OpenAI
V7-03 execution, public stubs, LocalFile data, and workflow state remain
unchanged.

Planning rollback is to revert this RFC and the matching V7-04 roadmap entry.
If a later implementation is approved, operational rollback is to remove or
disable only the explicit ComfyUI composition and return selection to the
unchanged mock default. Rollback must not delete accepted assets, erase
generation evidence, replay ambiguous attempts, or switch Providers.

If implementation later proposes persistent Provider-private state, it must
define forward and reverse compatibility in its separately approved scope
before writing that state.

## Validation plan

This docs-only design change requires:

- exact changed-file review proving only this RFC and `docs/ROADMAP_V7.md`
  changed;
- repository-available Markdown and local-link consistency checks;
- `git diff --check`;
- proof that no code, dependency, lockfile, package metadata, version, or
  release file changed; and
- independent read-only review with P0 = 0 and P1 = 0 before merge.

A later implementation must add executed evidence for:

- exact approved implementation allowlist and `git diff --check`;
- unchanged default mock, legacy stub, OpenAI V7-03, and no-network behavior;
- CLI-only explicit opt-in and durable human authorization acceptance and
  rejection cases;
- strict loopback parsing, DNS/remote/proxy/redirect/credential/scheme
  rejection, and same-origin enforcement;
- read-only health, core-node, and checkpoint preflight with no side effects;
- fixed graph validation and rejection of arbitrary workflows, custom nodes,
  scripts, altered edges, batch size, or multiple outputs;
- one Page, one admitted attempt, prompt-only input, and one PNG enforcement;
- exactly one `POST /prompt`, bounded `/history/{prompt_id}` observation, and
  same-origin `/view` byte retrieval;
- timeout, connection-loss, process-loss, malformed-response, and persistence
  ambiguity producing `RECOVERY_REQUIRED` with no resubmission, replacement,
  fallback, or Provider switch;
- unexpected content type, over-25-MB, malformed/truncated/trailing PNG,
  unsafe metadata, output-path, and multiple-output rejection;
- existing LocalFile containment, asset ownership, evidence, and external
  application behavior;
- StateMachine, `WorkflowEngine`, storyboard, quality-review, and explicit
  approval regressions;
- CLI, MCP, HTTP, Web UI, Repository, SDK, Plugin, public-import, and v5/v6
  compatibility; and
- applicable lint, type checking, focused and full regression, Windows
  security, audit, package, CI, and independent review gates.

## Acceptance criteria

This RFC is accepted when reviewers confirm that it:

- applies the V7-03 Provider-neutral LocalFile durable boundary to local
  ComfyUI as a second reference Provider without implementation;
- keeps the legacy `ComfyUIImageGenerator` as a deterministic non-network
  stub and keeps `mock` as the default;
- defines CLI-only explicit opt-in and durable human authorization as future
  first-slice prerequisites;
- restricts transport to validated loopback-only HTTP with no remote, LAN,
  DNS, proxy, redirect, wildcard, credential, or cloud surface;
- freezes a Manga Director-owned, fixed, core-node-only workflow graph and
  excludes arbitrary workflows, custom nodes, third-party packages, and
  scripts;
- bounds generation to one Page, one admitted attempt, prompt-only input, and
  exactly one PNG;
- defines one `POST /prompt`, bounded `/history/{prompt_id}` polling, and
  `/view` byte retrieval without mandatory WebSocket support;
- prohibits direct access to ComfyUI output paths and validates fetched bytes
  as strict PNG no larger than 25 MB before LocalFile ownership;
- treats submission ambiguity as `RECOVERY_REQUIRED` and prohibits automatic
  retry, replacement, fallback, or Provider switching;
- bundles no ComfyUI code, nodes, models, or checkpoints and authorizes no
  dependency change;
- preserves StateMachine, `WorkflowEngine`, storyboard, quality, approval,
  LocalFile, OpenAI V7-03, and public compatibility boundaries;
- remains completely independent of I02; and
- explicitly authorizes no implementation, live call, release, tag,
  publication, Settings, force push, branch deletion, or `main` change.

## Authorization gate

Acceptance of this RFC completes the V7-04 Design Freeze only. It does not
authorize V7-04 implementation or a live ComfyUI call. Before implementation,
a separate proposal must identify the exact file allowlist, concrete private
types, test changes, dependency result, security cases, migration result, and
executed quality gates, and must receive explicit approval.
