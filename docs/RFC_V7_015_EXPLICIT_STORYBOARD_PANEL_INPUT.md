# RFC-V7-015: Explicit Confirmed Storyboard Panel Input

- Status: Draft proposal; not accepted and not implementation authorization
- Related roadmap item: V7-17 — Explicit Confirmed Storyboard Panel Input
- Prerequisites: V7-15 local Web activation and V7-16 proof bridge
- Scope: Planning → Storyboard → PromptBuilt input completeness for the existing private LocalFile panel-generation path
- Frozen references: RFC-V7-012, RFC-V7-013, and RFC-V7-014 remain unchanged

## Problem

The normal `StoryboardAgent` currently supplies generic defaults such as
`protagonist` and `advance the page purpose`, and does not produce the complete
explicit panel fields required by V7-14. The V7-14 converter correctly rejects
missing or abstract values. V7-15 separately asks the user for supported panel
rectangles, and V7-16 proves outputs already applied; neither supplies the
missing Storyboard inputs.

This proposal adds an explicit user-confirmed input path at the existing legal
`Reviewed → Storyboarded` transition. It carries the user's exact panel intent
through the ordinary persisted Storyboard and PromptBuilt workflow, then lets
the existing V7-15 generation flow and V7-16 proof bridge consume it. It does
not change the legacy Storyboard action or generic `/generate` behavior.

## Existing authorities and limitations

- `Page.storyboard` and `Page.prompt` are already persisted dictionaries. The
  current V7-14 converter consumes ordered `Page.storyboard.panels` and the
  exact persisted PromptBuilt artifact. It requires, per panel, `number`,
  `narrative_intent`, `characters`, `continuity_bindings`, `action`,
  `background`, `composition`, and `constraints`.
- The frozen `PagePanelSpecification` allows at most 16 panels; it requires
  non-empty character, continuity, and constraint lists, limits those lists
  to 32, 32, and 64 items, limits text to 4,000 characters and list items to
  512 characters, and requires trimmed concrete values. The converter and
  frozen contracts remain authoritative for final acceptance.
- The current `Project.characters` field is an untyped list of dictionaries,
  not an established stable-character registry. Existing identity-pack
  validation does not create a general project-character registry contract.
- The current Page detail response exposes the persisted `page_design` and
  `review` artifacts, but not the LocalFile aggregate revision or fingerprint.
  Those values are aggregate-level, not Page-level. The LocalFile revisioned
  snapshot path may initialize or reconcile sidecars, so it cannot be used as
  a supposedly read-only preview operation.
- The accepted RFC-V7-011 source was located in the archived local reference
  worktree at `C:\Users\owner\Documents\Codex\2026-10-23\v7-e2e-61baeda\docs\RFC_V7_011_PANEL_AWARE_PAGE_GENERATION.md`; its SHA-256 matches the
  supplied authoritative digest. Reconcile this proposal with that source
  before implementation approval; do not reconstruct or replace the frozen
  RFC. RFC-V7-012 through RFC-V7-014 and executable contracts remain additional
  verified design evidence.

## Recommended design

### 1. Add a LocalFile-only confirmation route

Add one optional loopback-only submit route in the existing LocalFile HTTP
composition. This is an additive HTTP request/response contract; existing
endpoints and DTO shapes remain unchanged. Do not expose a public Python
export, CLI, MCP, SDK, remote route, or Provider contract. Use the existing
Page detail response for the displayed `page_design` and `review` artifacts;
do not add a preview/read route or read revision sidecars to support the form.

The user-confirmation route is:

```text
POST /projects/{project_id}/pages/{page_number}/storyboard/confirm
```

Its closed, versioned request has exactly these top-level fields:

```json
{
  "requestVersion": 1,
  "expectedSource": {
    "state": "Reviewed",
    "page_design": {},
    "review": {}
  },
  "confirmed": true,
  "panels": []
}
```

`expectedSource` is captured immutably from the exact displayed Page detail
values at the time the user begins confirmation. Its `state` must be the
literal `Reviewed`; its `page_design` and `review` values are the exact
`artifacts.pageDesign` and `artifacts.review` dictionaries. These values are
only a stale-content comparison and are never merged or persisted.
The root envelope has exactly the keys shown; `expectedSource` has exactly
`state`, `page_design`, and `review`. The nested artifact dictionaries are
opaque existing JSON values, not an extensible authorization channel. Bound
the entire request body to 32,768 bytes, nesting depth to 16, and total JSON
nodes to 4,096; those aggregate limits apply in addition to the per-panel field
and list maxima below and do not promise that every request using all
per-field maxima fits the body cap. Reject non-finite numbers, unsupported
JSON values, duplicate object keys, and any type/value that cannot be
represented without loss by the existing API JSON round trip. The displayed
capture is immutable until submit; if the Page is refreshed or its source
changes, the user reviews the new values and confirms again.

Each ordered `panels` entry has exactly the V7-14 source keys `number`,
`narrative_intent`, `characters`, `continuity_bindings`, `action`,
`background`, `composition`, and `constraints`. Reject unknown keys, absent
fields, non-contiguous or reordered panel numbers, wrong primitive types,
empty values, untrimmed text, abstract placeholders, over-limit values,
duplicate IDs, and unsupported panel counts. Each character ID is a bounded
ASCII logical reference matching `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`. The exact
ID is retained wherever the same character appears; the user supplies that
identity consistently, and no registry lookup or identity inference occurs.
Require an explicit affirmative
confirmation in the request. The server validates all fields independently;
it does not trust browser-side field validation.

Before the `Reviewed → Storyboarded` transition, the dedicated gate also
preflights the exact confirmed input against the existing deterministic
PromptPipeline and PromptValidator prerequisites, including the existing
character limit on newline-joined structured-prompt section values after
optimization and before rendering, template compatibility, and
source-character requirements. Inputs that cannot pass the existing
PromptBuilt path are rejected as bounded
`invalid_input` before any Page or artifact mutation. Do not raise existing
limits, alter templates, or infer missing prompt/source values to make an
input pass. This avoids accepting and persisting a confirmation that cannot
advance through the ordinary PromptBuilt transition.

Under the Page fence, the server constructs this exact authoritative source
projection:

```json
{
  "kind": "reviewed_storyboard_source_v1",
  "version": 1,
  "project_id": "<project id>",
  "page_number": 1,
  "source": {
    "state": "Reviewed",
    "page_design": {},
    "review": {}
  }
}
```

Before application access, the route applies the existing same-origin
browser-write admission used for LocalFile routes: fixed canonical path, no
query string, exactly one accepted `Origin`, `Referer`, `Content-Type`,
`Accept`, fetch metadata, and `Content-Length` header; origin
must be local and equal to the allowed referer origin; `Sec-Fetch-Site` is
`same-origin`, `Sec-Fetch-Mode` is `cors`, `Sec-Fetch-Dest` is `empty`, media
type is JSON, `Transfer-Encoding` is absent, and the body is no larger than
32,768 bytes. Reject duplicate JSON object keys, unknown envelope keys, and
malformed or noncanonical route values before application access. Parse the
bounded raw body with duplicate-key detection rather than relying on a DTO
parser that may discard duplicate members. The Web
same-origin proxy uses only the fixed loopback backend destination, validates
its browser request metadata and exact body bound, forwards an explicit header
allowlist, and does not follow redirects. These local checks do not provide
authentication or identity proof.

Success returns HTTP 200 with `{"status":"storyboarded"}`. Invalid or
malformed requests return HTTP 422 with a bounded `invalid_input` code; an
unknown project/Page returns HTTP 404 `not_found`; a source mismatch or Page
state that no longer permits the transition returns HTTP 409
`confirmation_conflict`; and an unavailable durable activation returns HTTP
503 `activation_unavailable`. Error responses contain no input or authority
object. On an uncertain 503, the Web UI tells the user to reload and inspect
Page state; it does not retry automatically. Concurrent duplicate submissions
are serialized by the existing fence: at most one may transition, and the
other receives a conflict after observing the new state.

The route requires `expectedSource` to match the `source` object from the
fresh authoritative projection exactly, including strict value types. It
never merges or persists the caller's copies. It accepts only a fresh
authoritative `Reviewed` Page for
which the existing StateMachine allows `storyboard`. A mismatch returns a
conflict with no Page/artifact/event mutation or Provider invocation. The
normal LocalFile durable command boundary may perform its existing revisioned
state access; rejected requests are not described as proving that no internal
durability sidecar was initialized. The gate must add no new sidecar, owner,
schema, migration, repair, or provider action. The server captures the current
aggregate revision and fingerprint from the same authoritative snapshot only
into the fenced, process-local authority and existing CAS binding. It never
accepts those values from the client, persists or publishes them, or predicts
the post-commit fingerprint.

### 2. Keep confirmation authority process-local and one-use

Use a private, immutable, exact-type `_ExplicitStoryboardInputAuthority`
capability created only by the dedicated confirmation gate after validating
the closed request and the fenced Reviewed snapshot. It binds the exact
Project ID, Page number, source aggregate revision/fingerprint, captured
panel values, canonical panel digest, and source artifact digests. It cannot
be constructed from caller JSON or a mutable dictionary.

Do not place the capability in `WorkflowContext`, workflow metadata, or any
public or serializable input passed to the WorkflowEngine. The private
invocation-only scope factory described below is the sole exception; it holds
the authority only for the call and is not stored or serialized. Keep it in a
dedicated private `ContextVar` scope owned by the LocalFile durable execution
boundary. Only the dedicated confirmation gate may create the exact-type
authority, after
validating the closed request and fenced `Reviewed` snapshot. The durable
execution boundary creates a private one-call scope factory that holds the
authority and sets a `ContextVar` token only when the WorkflowEngine enters
the authorized Storyboard agent call. Extend the private
`WorkflowEngine._execute_unpublished()` seam with an invocation-only scope
hook: call `observer.begin(context, next_state)` first, then enter the hook
immediately around `agent.execute(context)`, and reset the token in `finally`
before exception handling (`observer.fail`), transition/result construction,
or any persistence, publication, or observer completion. Do not set the
variable around the whole engine call. The scope factory is private to the
LocalFile durable path and is never stored on the shared engine or passed to
observers, the `WorkflowContext`, or workflow metadata. The existing
`WorkflowContext`, its metadata, and observer arguments therefore remain
authority-free from the start, and a nested generic WorkflowEngine call from
`observer.begin` runs without the authority scope. In the existing
`StoryboardAgent.execute()` dispatch, `builtin.py` must consume and clear the
exact type from the private `ContextVar` immediately at agent entry, before
validation, logging, or any callback, then recheck its exact Project/Page/source
binding before using the captured panel values. The explicit projection must
not invoke callbacks, LLMs, or support agents while the authority is held in a
local variable. No other workflow action may consume it. Preserve the existing
no-agent-to-agent-call rule; StoryboardAgent must not reenter the
WorkflowEngine. “One-use” means one successful legal transition: fresh
`Reviewed` state plus the existing Page fence and CAS enforce consumption.
This adds no cryptographic nonce or consumption store. The generic
`storyboard`, `prompt`, and `generate` `_COMMAND_OVERLAY_KEYS` remain empty.
Do not widen ordinary `PageActionRequest` metadata. Only the dedicated route
may invoke the private LocalFile gate, and that gate accepts only the exact
capability type for the exact Project/Page at `Reviewed`. Reject the reserved
capability key in caller-supplied or persisted context metadata before an
ordinary command, but never use that key to transport or recover the
authority.

For rejected requests, do not create the scope. Since CAS, post-commit
verification, and event publication occur after `agent.execute()` and after
the scope hook has reset its token, those later failures must also observe an
empty scope. Keep an active-scope sentinel separate from the consumed
authority: clearing the authority at agent entry must not make a nested
dedicated scope appear inactive. Nested dedicated scopes must fail closed, and
both tokens must reset in `finally`, restoring their prior values rather than
clearing another scope's state. No shared mutable “current Page” state is
allowed. The current `WorkflowEngine` is synchronous and calls
`observer.begin(context, next_state)` before `agent.execute(context)` in the
same execution context; the private hook keeps the observer outside the
authority scope, including a nested generic engine call from that observer.
The engine's exception path calls `observer.fail` after the agent call, so the
hook must have reset the token before that callback too. An observer still
receives an authority-free `WorkflowContext`. If an observer or plugin is
treated as hostile in-process code that can inspect live Python stack frames
or private closures, this design is insufficient and implementation must stop
for stronger isolation.

Python `ContextVar` values are local to an execution context, but child
asyncio tasks copy the current context when they are created, and
context-copying worker helpers can propagate it as well. Independent concurrent
tasks do not share later changes. Therefore the scoped agent call must not
create child tasks, copy its context, or invoke context-copying worker helpers;
the current synchronous agent execution must finish before token reset. Any
future task or worker handoff must start with an explicitly authority-free
context and may not consume the authority. Audit any WorkflowEngine, observer,
or task-creation change before implementation to confirm this rule still
holds. A `ContextVar` is not an authentication or
authorization mechanism: the route, exact-type/source binding checks, existing
StateMachine, Page fence, and CAS remain authoritative. It cannot protect
against deliberate access by code already running in the same Python process.

The legacy Storyboard path with no private confirmation capability retains its
current behavior.

On a Reviewed Page where both the legacy Storyboard action and explicit panel
confirmation are available, the Web UI clearly distinguishes the two and
identifies explicit confirmation as the path for supplying the required V7-14
fields. Explain that the legacy action may omit those fields and may not pass
V7-14 conversion. Either choice remains subject to the existing
server-authorized `Reviewed → Storyboarded` transition. When either transition
succeeds, the other control is stale; reload authoritative Page state and do
not automatically retry, reconfirm, or roll back.

In the same existing `StoryboardAgent.execute()` dispatch,
the dedicated path consumes only the exact private capability and creates
`panels` from the captured user values without invoking an LLM, filling gaps,
or rewriting fields. The confirmed `Page.storyboard` root has exactly `panels`
and `confirmation`; each confirmed panel has exactly the listed V7-14 source
fields, without legacy `role`, `camera`, dialogue, or display-only keys. The
dedicated output adds a closed root `confirmation` object with exactly these
keys: `schema_id`, `schema_version`, `source_project_id`,
`source_page_number`, `source_sha256`, `source_page_design_sha256`,
`source_review_sha256`, `panel_input_sha256`, and `user_confirmed`.
`schema_id` is the fixed
`manga_director.explicit_storyboard_input`; `schema_version` is integer `1`;
`user_confirmed` is the literal boolean `true`. Digests use lowercase SHA-256
hex strings of exactly 64 characters. `source_page_number` is a strict
positive integer and `source_project_id` is the exact canonical Project ID
from the route. This object records content provenance; it is not
authenticated identity, authorization, or Human Approval.

Canonical JSON for digest calculation uses UTF-8, `ensure_ascii=False`, sorted
object keys, compact separators, rejects NaN/infinity, and has no trailing
newline. `panel_input_sha256` hashes only the canonical ordered `panels`
array, excluding the confirmation object. `source_page_design_sha256` and
`source_review_sha256` hash the complete canonical source artifact dictionaries
from the same Reviewed snapshot. This avoids a self-referential digest.
`source_sha256` hashes the closed `reviewed_storyboard_source_v1` object above
using the server-captured Project/Page identity and source dictionaries. The
normal V7-14 conversion subsequently hashes the entire persisted Storyboard
and PromptBuilt dictionaries using its existing derivation rules.

Because the capability never enters workflow metadata, it must already be
absent from `project_from_context`, every returned `WorkflowResult`, and every
publication; do not rely on post-hoc sanitization. The capability or its
internal binding, raw request envelope, aggregate source revision or
fingerprint, credentials, and authorization-bearing values must never enter
the persisted Project, canonical event, Page detail, application logs,
exception diagnostics or tracebacks, observer output, or debug serialization.
Error responses expose only bounded safe codes. The persisted Storyboard
contains only the closed provenance object defined above and exact confirmed
panel values.

### 3. Validate the confirmed input again when building PromptBuilt

Inside the existing fenced `prompt` command path, inspect the persisted
Storyboard before invoking `PromptAgent`:

- If the reserved root `confirmation` field is absent, preserve the existing
  legacy PromptBuilt behavior.
- If present, require the exact closed schema above; reject malformed,
  unknown, missing, or wrong-type fields.
- Recompute and compare `panel_input_sha256` over the exact ordered panel
  array. Recompute `source_page_design_sha256` and `source_review_sha256` from
  fresh current artifacts, and compare each digest with its saved counterpart.
  Then rebuild the closed source binding with literal historical
  `source.state = "Reviewed"`, stored source Project/Page identity, and those
  fresh artifact values. Compare its `source_sha256` with the saved source
  digest. The current workflow state is `Storyboarded` here and is not
  substituted for the historical source state.
- Check exact Project/Page binding, strict panel numbering, field shape, and
  frozen V7-14 bounds. Any mismatch fails closed before the Prompt agent is
  invoked, with no Page/artifact/event mutation or Provider call; the existing
  LocalFile durability reconciliation semantics remain unchanged.

The aggregate revision and fingerprint bind only the fenced, process-local
authority and existing CAS boundary at the Reviewed snapshot. They are not
fields of the persisted confirmation and are not copied into Page artifacts,
returned results, events, or Page detail. Later PromptBuilt provenance checks
use the exact content digests and Project/Page binding without relying on a
predicted post-transition fingerprint. The ordinary PromptPipeline may format
or optimize rendered text; this RFC guarantees preservation of the exact
confirmed structured panel source, not identical PromptBuilt prose. Existing
V7-14 panel conversion remains based on the persisted structured Storyboard,
not inferred fields extracted from Prompt prose.

Any edit to the displayed reviewed source artifacts before confirmation
causes an exact source-projection conflict. Any source mutation after
confirmation and before PromptBuilt fails the digest check. A replacement
Storyboard requires a new user confirmation at a fresh `Reviewed` state; no
automatic reconfirmation is permitted.

### 4. Identity, layout, and approval boundaries

Treat `characters` as exact user-supplied, bounded, project-scoped stable ID
strings. Require explicit values and reject duplicates within a panel; retain
exact spelling across panels. Do not map display names to IDs, mint IDs, infer
identity from an LLM or another artifact, or claim a global identity registry.
Panels without characters are out of scope because the frozen plan
requires at least one character identity, continuity binding, and constraint;
do not invent a sentinel such as `none`. Supporting no-character panels
requires a separate frozen-contract decision.

The user explicitly supplies continuity, action, background, composition,
constraints, and narrative intent. No AI suggestion may silently populate,
rewrite, or save these confirmed fields. Empty or unsupported values stop the
path. Geometry remains separate: V7-15 continues to require the explicit
supported layout profile and ordered rectangles. This RFC neither auto-fills
nor persists geometry.

The confirmation is a local provenance record in an unauthenticated local
workflow. It does not prove who operated the machine, defend against a person
who can edit local files, replace the existing authentication boundary, or
approve an image. Existing StateMachine, LocalFile authorization, V7-15
activation, V7-16 output proof, Visual QA, and explicit Human Approval remain
authoritative and unchanged.

## Alternatives and recommendation

| Option | Compatibility and safety | Decision |
| --- | --- | --- |
| Add a typed envelope to generic `PageActionRequest.metadata` or widen the `storyboard` overlay | Existing generic callers could forge or replay the same values; this changes an existing entry point and overlay contract. | Reject. Keep generic metadata and the empty storyboard overlay unchanged. |
| Add a new GET source-version/preview endpoint | The LocalFile revisioned snapshot read is not side-effect-free; exposing aggregate revisions adds an observer surface and false conflicts from unrelated Page changes. | Reject. Use the exact source artifacts already displayed by Page detail and compare them under the existing Page fence. |
| Dedicated LocalFile confirmation route with exact source projection and transient exact-type authority | Additive opt-in route; binds user-entered panels to current Reviewed source and routes through the existing StateMachine, Page fence, CAS, and EventBus. | Recommend. Smallest option that provides an explicit confirmation boundary without changing ordinary actions or adding persistence authority. |

## Rollback and removal

This proposal adds no database migration, new Page model field, or external
service dependency. If a later approved implementation must be withdrawn,
disable/remove the new Web control and dedicated confirmation route, then
revert the allowlisted application and validation changes together. Preserve
already-written `Page.storyboard.confirmation` dictionaries; do not attempt an
automatic Page-state rollback or data rewrite. Before implementation is
approved, a compatibility test must prove the supported prior version safely
ignores the additive dictionary key. If that cannot be proven, stop and add a
separately reviewed data-compatibility plan. No rollback or source revert is
authorized by this draft.

## Exact future implementation allowlist

This list is a design estimate for a later implementation approval. It is not
authorization to edit or test these files. If implementation needs any other
file, a persisted schema/migration, changes to a frozen contract, or a widened
generic overlay, stop and obtain a revised design and explicit approval.

### Source files

1. `src/manga_director/api/workflow.py` — closed confirmation request and
   response DTOs and LocalFile-only route composition.
2. `src/manga_director/application/workflow.py` — dedicated confirmation use
   case; preserve ordinary `execute_page` behavior.
3. `src/manga_director/production/explicit_storyboard_input.py` — new private,
   immutable closed input/provenance contract, validation, and canonical
   digest functions.
4. `src/manga_director/workflow/durable_execution.py` — fenced private
   confirmation gate, PromptBuilt provenance validation, and the private
   one-call scope factory; no authority in workflow context or metadata.
5. `src/manga_director/workflow/engine.py` — extend the private unpublished
   execution seam with a per-invocation agent-scope hook that runs after
   `observer.begin` and around only `agent.execute`, resetting in `finally`.
6. `src/manga_director/agents/builtin.py` — consume the exact private
   capability to project confirmed Storyboard fields; preserve the legacy path.
7. `web/lib/api/types.ts` — additive request/response types.
8. `web/lib/api/client.ts` — additive confirmation client method.
9. `web/app/api/projects/[projectId]/pages/[pageNumber]/storyboard/confirm/route.ts`
   — new same-origin proxy to the LocalFile confirmation route.
10. `web/components/page-workflow.tsx` — render the explicit input flow only
    for eligible Reviewed Pages.
11. `web/components/explicit-storyboard-input-form.tsx` — new explicit panel
    editor, immutable source capture, validation, and final confirmation
    control.

### Test files

1. `tests/test_workflow_http_api.py` — closed body, route availability and
   error mapping; unchanged ordinary routes.
2. `tests/test_workflow_application.py` — dedicated use case, legacy path
   compatibility, and non-LocalFile behavior.
3. `tests/unit/test_agents.py` — exact confirmed projection and unchanged
   legacy Storyboard behavior.
4. `tests/unit/test_workflow_engine.py` — private hook ordering after
   `observer.begin`, reset before `observer.fail`, transition/result creation,
   and publication; public `execute`/`execute_command` expose no hook; nested
   generic observer reentry cannot consume the dedicated authority; nested
   dedicated scope fails closed even after the agent consumes and clears the
   authority, using the separate active-scope sentinel.
5. `tests/test_localfile_explicit_storyboard_input.py` — LocalFile integration
   coverage for:
   - source-projection mismatch under the fence; forged/replayed authority
     attempts through caller metadata and persisted context; malformed saved
     confirmation; source mutation before Prompt; and structured-prompt
     validator rejection before Storyboard mutation;
   - observer-before-agent ordering; a nested generic WorkflowEngine call from
     an observer receiving no authority scope; the private hook entering only
     around the authorized StoryboardAgent; nested dedicated scope rejection
     after authority consumption; and token reset/restoration on
     success, rejection, agent failure, cancellation, CAS failure, post-commit
     verification failure, and event-publication failure;
   - independent concurrent Page isolation; a probe confirming that copied
     `ContextVar` contexts would inherit the value; and proof that the
     authorized agent scope creates no child task, copied context, or worker
     handoff and that any later handoff starts authority-free;
   - absence of capability/raw request from persisted Project, returned
     result, event, and Page detail; absence of aggregate source revision and
     fingerprint from the persisted confirmation after reload, serialized
     Project, returned `WorkflowResult`, canonical event, and Page detail;
   - logs, exception diagnostics/tracebacks, observer output, and debug
     serialization containing none of the authority, binding, raw request,
     aggregate revision/fingerprint, credentials, or authorization-bearing
     values on success, rejection, agent failure, cancellation, CAS failure,
     post-commit verification failure, and event-publication failure; and
     exact Storyboard reload, Prompt transition, legacy action, and unchanged
     generic `/generate` behavior.
6. `tests/test_localfile_panel_aware_generation_http.py` — full fake-transport
   one-Page chain from confirmed normal Storyboard/PromptBuilt through existing
   V7-15 generation and V7-16 output proof, Visual QA, Human Approval, and
   approved download.
7. `web/tests/explicit-storyboard-input.test.ts` — new UI behavior,
   required-field validation, explicit confirmation, changed-source refresh,
   and no duplicate submission; distinct labels and guidance for legacy Storyboard
   versus explicit confirmation; after a legacy transition, the captured form
   is stale and requires reload without automatic retry or reconfirmation.
8. `web/tests/api-client.test.ts` — confirmation client path and closed body.
9. `web/tests/ui-contract.test.ts` — Reviewed-only affordance.
10. `web/tests/storyboard-confirm-proxy.test.ts` — new same-origin proxy
    forwarding and error mapping.
11. `tests/test_localfile_panel_aware_activation_bridge.py` — converter
    compatibility coverage for confirmed persisted Storyboard; the frozen
    converter itself is not in the allowlist.

## Acceptance criteria

- No preview route or revision-sidecar read is added; the client submits the
  exact source artifacts currently displayed by the existing Page detail.
- Only one exact closed confirmed request whose source projection matches the
  authoritative Reviewed Page can perform the normal StateMachine `storyboard`
  transition under the existing Page fence.
- Generic `PageActionRequest.metadata`, persisted metadata, or a forged
  reserved key can never create or reuse the process-local authority. The
  authority never enters `WorkflowContext` or workflow metadata, and generic
  overlay keys for `storyboard`, `prompt`, and `generate` remain empty.
- Confirmed panel fields round-trip exactly through persisted Storyboard and
  reload. No missing field is inferred or silently filled.
- Inputs that fail existing PromptPipeline/PromptValidator prerequisites are
  rejected before the Storyboarded transition, without changing prompt limits
  or templates.
- PromptBuilt accepts a valid confirmation only when the panel digest and
  source page-design/review digests still match the same authoritative
  Project/Page; malformed or stale provenance fails closed before PromptAgent.
- The transient authority and its internal binding, raw request envelope,
  aggregate source revision/fingerprint, credentials, and authorization-bearing
  values never appear in persistence, result, canonical event, Page detail,
  application logs, exception diagnostics/tracebacks, observer output, or debug
  serialization, including failure paths. Error responses expose only bounded
  safe codes. The workflow context and its metadata are authority-free from
  construction. An invocation-only WorkflowEngine hook enters the private
  scope after `observer.begin`, around only the authorized StoryboardAgent
  call, consumes/clears the authority at agent entry, and resets both the
  authority and active-scope tokens on every exit, including cancellation;
  nested dedicated scopes fail closed.
- Tests verify actual `ContextVar` behavior for concurrent Pages and copied
  contexts, that nested generic engine calls from observers lack the hook, and
  that no child-task/context-copy/worker handoff occurs while authority is
  active. Any later handoff must start authority-free. The private
  `ContextVar` is explicitly not authentication or
  authorization; existing server, StateMachine, Page fence, and CAS checks
  remain authoritative.
- Aggregate source revision and fingerprint remain process-local to the
  fenced authority and existing CAS boundary. They are absent from the
  persisted confirmation after reload, the serialized Project, returned
  `WorkflowResult`, canonical event, and Page detail response.
- When both Storyboard choices are available, the Web UI clearly distinguishes
  explicit panel confirmation from the legacy Storyboard action and explains that
  the legacy action may omit fields required by V7-14 conversion. After either
  transition succeeds, the other captured form is stale and requires Page reload;
  it must not automatically retry, reconfirm, or roll back.
- Legacy Storyboard and generic `/generate`, V7-15 explicit geometry,
  StateMachine, existing LocalFile authorization, V7-16 proof, Visual QA, and
  Human Approval behavior remain unchanged.
- Full flow can reach existing V7-14 conversion only when all frozen fields
  and separately supplied supported geometry are valid. No live Provider is
  needed for the fake-transport validation.

## Bounded validation plan for a later approved implementation

1. Run the new focused LocalFile and frontend tests, including changed-source
   confirmation requests, confirm-to-Prompt source mutations, concurrent
   submission, observer-before-agent ordering and nested generic engine calls,
   all `ContextVar` token reset/restoration paths, concurrent Page isolation,
   copied-context propagation probes, prohibition of child/worker handoff while
   active, and observer/diagnostic non-exposure.
2. Run existing workflow/StateMachine, V7-14 converter and V7-16 proof bridge,
   V7-15 panel-aware HTTP/Web, LocalFile security, and v6 regressions.
3. Run Ruff, mypy, frontend lint/typecheck/build, applicable security/audit
   checks, and `git diff --check`; report unavailable checks as pending.
4. Obtain a separate GPT-6.1 Sol High read-only review of the exact approved
   implementation diff before any later completion judgment. P0/P1 findings
   block merge or publication.

This plan does not run now. The present scope authorizes documentation only.

## Approval boundaries and unresolved prerequisite

Accepting this RFC, editing the roadmap, or selecting the proposed model does
not authorize implementation. The authoritative RFC-V7-011 source has now been
located and its supplied SHA-256 verified; implementation planning must
reconcile its frozen-contract implications before a separate explicit
approval of the exact implementation allowlist. No frozen RFC is amended here.
Stop if reconciliation finds a conflict; propose the smallest separate design
change and request approval rather than silently changing a frozen contract.

No change to V6 LTS, I02, dependencies, database/schema/migration, public
Python APIs, CLI, MCP, SDK, remote routing, authentication, Provider behavior,
`main`, branch state, release, or publication is included or authorized.
