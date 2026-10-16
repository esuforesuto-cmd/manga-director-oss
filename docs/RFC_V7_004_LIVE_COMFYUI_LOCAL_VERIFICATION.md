# RFC-V7-004: Live ComfyUI Local Verification Gate

- Status: Design frozen; no additional live generation or implementation authorized
- Target line: v7.0 Discovery (Post-LTS)
- Related roadmap item: V7-05 Live ComfyUI Local Verification Gate
- Reference Provider: local ComfyUI server
- Verified baseline: ComfyUI 0.40.0 on `http://127.0.0.1:8188`
- Delivery boundary: one explicitly authorized CLI-only verification attempt

## Decision boundary

This RFC freezes the smallest safe and repeatable gate for proving that the
V7-04 ComfyUI Local Provider can complete one real local generation without
weakening the existing durable admission, Provider-start, asset, workflow, or
compatibility boundaries.

The design is based on the completed V7-05 verification and the remediation
merged by PR #28. It records the verified contract after that bounded run; it
does not retroactively authorize implementation and does not authorize another
live request. Any future live verification requires its own explicit
authorization naming the exact Project, Page, Provider, endpoint, checkpoint,
source revision, and one-attempt limit.

This RFC and the matching roadmap update are docs-only. They do not authorize
code changes, Project creation, `POST /prompt`, image generation, dependency or
lockfile changes, I02, `main`, versioning, release, tag, publication,
repository settings, branch deletion, force push, or history rewriting.

## Problem

V7-04 proved the ComfyUI path with deterministic local tests, but tests alone
could not prove compatibility with an installed ComfyUI server, checkpoint,
device, real execution duration, returned output descriptor, or the complete
LocalFile asset-registration path.

The first live verification exposed five bounded integration gaps:

1. relative LocalFile durability roots needed resolution against the
   configuration directory;
2. persisted prompt text needed normalization before fixed-graph construction;
3. fixed-graph preparation and validation needed to complete before the
   durable Provider-start boundary was consumed;
4. the bounded polling window needed to accommodate a real local generation;
5. ComfyUI 0.40.0 output descriptors could include validated `metadata` and
   `id` fields that must be accepted without becoming lookup or filesystem
   authority.

PR #28 addressed those gaps without changing the public API, DTOs,
StateMachine, LocalFile schema, dependency set, mock default, OpenAI V7-03
behavior, or I02 boundary. A durable design is required so a future verifier
cannot turn that success into an unbounded smoke test, automatic retry loop, or
general-purpose ComfyUI execution facility.

## Planning summary

- **Title:** V7-05 Live ComfyUI Local Verification Gate.
- **Objective:** Freeze the repeatable, one-shot evidence gate proven by the
  completed V7-05 run without authorizing another live call or source change.
- **Scope:** Read-only preflight, separately authorized Project preparation,
  one durable attempt, fixed-graph preparation, one Provider start, bounded
  result observation, strict PNG and asset evidence, and post-run no-diff
  verification.
- **Inputs:** An exact source commit, one dedicated Project/Page identity, one
  persisted prompt, one loopback endpoint, one installed checkpoint name, and
  one explicit human authorization record.
- **Outputs:** A PASS, NOT_READY, or BLOCKED decision plus bounded evidence for
  the attempt, Provider start, result observation, PNG, asset registration,
  Page transition, and repository state.
- **Dependencies:** Completed V7-04 contracts, the existing LocalFile durable
  chain, fixed core-node graph, local ComfyUI installation, installed local
  checkpoint, and existing validation/review gates. No new package dependency
  is permitted.
- **Estimated complexity:** Small docs-only change; medium operational risk for
  any separately approved future live run because it creates an external side
  effect that cannot be retried safely when ambiguous.
- **Architecture notes:** The gate composes existing private V7-04 boundaries
  and adds no public contract, state, persistence schema, retry authority, or
  runtime component.

## Goals

- Define the exact preconditions for one separately approved live local
  ComfyUI verification.
- Preserve one Page, one admitted attempt, one Provider start, one selected
  PNG, and no automatic retry.
- Separate read-only environment and repository preflight from the single
  external side effect.
- Require fixed-graph construction and validation before durable
  `PROVIDER_STARTED` evidence is recorded.
- Treat all ComfyUI result fields as untrusted input and retain only the
  minimum validated lookup fields.
- Prove durable attempt completion, evidence readiness, asset registration,
  strict PNG validation, and legal Page transition together.
- Leave source and repository state unchanged by the live verification itself.
- Produce enough evidence to distinguish PASS, NOT_READY, and BLOCKED without
  guessing or resubmitting.

## Non-goals

V7-05 does not include:

- another live generation under this RFC;
- routine, scheduled, background, batch, parallel, or autonomous smoke tests;
- automatic retry, replacement attempt, fallback, or Provider switching;
- remote, LAN, DNS, cloud, proxy, tunnel, wildcard, or authenticated ComfyUI
  endpoints;
- starting, stopping, upgrading, configuring, or exposing ComfyUI;
- model or custom-node download, installation, update, or execution;
- arbitrary workflow JSON, user-edited graphs, custom nodes, embedded scripts,
  reference images, image-to-image input, or multi-image output;
- performance, visual-quality, model-quality, or character-consistency
  benchmarking;
- public API, DTO, StateMachine, WorkflowEngine, LocalFile schema, HTTP, Web,
  MCP, SDK, Plugin, or package changes;
- dependency, lockfile, version, release, tag, publication, Settings, `main`,
  force-push, branch-deletion, or history-rewrite work; or
- I02 authority, imports, persistence, contracts, or implementation.

## Frozen verification architecture

```text
Explicit human authorization for one exact live verification
                              |
                              v
Phase A read-only repository, environment, endpoint, node, and checkpoint preflight
                              |
                              v
Separately authorized dedicated Project preparation to one PromptBuilt Page
                              |
                              v
Phase B read-only final preflight for the exact Project, Page, and environment
                              |
                              v
Durable admission plus prompt normalization
                              |
                              v
Build and validate the fixed core-node graph without POSTing
                              |
                              v
Persist PROVIDER_STARTED immediately before one POST /prompt
                              |
                              v
Bounded observation of the same prompt_id and same-origin /view bytes
                              |
                              v
Strict PNG and 25 MB validation -> LocalDurableAssetOwner
                              |
                              v
Existing WorkflowEngine/StateMachine application -> Page Generated
                              |
                              v
Read-only evidence capture and repository no-diff verification
```

The gate coordinates existing private V7-04 components. It creates no new
public service, DTO, schema, command, state, retry authority, or recovery API.

## Approval package

A live verification approval must identify one bounded package:

- source repository and exact commit;
- dedicated Project ID and Page number;
- expected pre-run Page state of `PromptBuilt`;
- Provider selection `comfyui`;
- exact loopback endpoint `http://127.0.0.1:8188`;
- exact checkpoint name;
- non-empty human authorization evidence;
- maximum of one admitted attempt and one `POST /prompt`;
- required result and repository evidence; and
- explicit exclusions, including retry, fallback, another Provider, I02,
  dependency changes, and source modification during the run.

Project preparation is permitted only when the approval package explicitly
includes it. Live-generation authorization is consumed when the one permitted
durable attempt is admitted. The distinct Provider-start opportunity is
consumed immediately before the single POST. An early read-only preflight
failure does not consume the live request, but it does not authorize the
verifier to start or repair ComfyUI, download a model, change configuration,
modify source, or broaden the package.

## Read-only preflight

Every live attempt has two fresh, recorded preflight phases. Phase A occurs
before any approved Project preparation and verifies repository and external
environment readiness. Phase B occurs after the dedicated Page reaches
`PromptBuilt` and immediately before durable attempt admission. Across the two
phases, the gate must verify:

1. the repository, branch, exact commit, allowlisted diff, staged state, and
   `git diff --check` result match the approved package;
2. the dedicated Project exists, contains exactly the intended Page, and the
   Page is `PromptBuilt` with no registered generated image;
3. no prior durability attempt for that exact live package exists;
4. `127.0.0.1:8188` is the only accepted destination and the endpoint remains
   loopback-only;
5. bounded read-only ComfyUI health and system information calls succeed;
6. the expected ComfyUI version and device are recorded as evidence rather
   than treated as compatibility authority;
7. all six required node types are present as core nodes whose
   `python_module` is `nodes`:
   `CheckpointLoaderSimple`, `CLIPTextEncode`, `EmptyLatentImage`, `KSampler`,
   `VAEDecode`, and `SaveImage`;
8. the exact configured checkpoint name appears in the server-reported
   checkpoint list; and
9. queue and history observations do not reveal a conflicting request for the
   same verification identity.

Both preflight phases use GET/read-only observations only. Project creation and
legal advancement to `PromptBuilt`, when explicitly authorized, occur between
the phases through existing CLI and workflow authority rather than inside a
preflight. Neither phase may create an attempt, queue work, upload input,
install anything, or invoke `POST /prompt`.

The gate reports:

- `PASS` only when every precondition is satisfied;
- `NOT_READY` when an approved prerequisite can be supplied later without
  changing the design, such as ComfyUI not currently listening; or
- `BLOCKED` when evidence conflicts, a prior attempt exists, the repository is
  outside the approved package, or safe execution would require scope
  expansion.

## Project and prompt boundary

The live gate uses a dedicated, uniquely named Project and one Page. The Page
must be advanced through the existing legal workflow to `PromptBuilt`; the
gate does not bypass storyboard, prompt, workflow, or approval authority.

Persisted prompt text is authoritative input but is normalized with the same
bounded whitespace rule before it enters the fixed graph. Empty prompt
material remains invalid. Normalization must not rewrite the persisted prompt,
invent content, or change evidence identity.

A relative LocalFile repository or durability root is resolved against the
configuration file directory. It must not depend on the process working
directory. Existing containment, ownership, and path-safety checks remain
authoritative after resolution.

## Provider-start and one-shot semantics

All deterministic work that can fail without an external side effect must
finish before Provider start, including:

- durable input and binding validation;
- prompt normalization;
- fixed graph construction;
- fixed graph validation; and
- Provider-private request preparation.

Preparation must not call ComfyUI. A preparation failure reports no Provider
invocation and creates no `POST /prompt`.

After successful preparation, the existing durable chain records the consumed
Provider-start opportunity immediately before invoking the prepared request.
The request may issue `POST /prompt` exactly once. Only the returned
`prompt_id` may be observed through bounded history polling. Polling may repeat
for that identifier within the approved time window; it cannot submit again.

Timeout, connection loss, process loss, malformed submission response, missing
identifier, observation failure, persistence failure, or any ambiguity after
Provider start becomes `RECOVERY_REQUIRED`. The verifier must not repeat POST,
create a replacement attempt, switch Provider, or claim that generation did
not occur.

## Polling and ComfyUI 0.40.0 compatibility

The polling window is finite and must cover the regression case in which
history remains pending for 10.5 simulated seconds before exposing the output.
The gate records the configured bound and the live run's observed duration; it
does not adapt indefinitely or treat a slower result as permission to retry.

The expected output descriptor contains `filename`, `subfolder`, and `type`.
ComfyUI 0.40.0 may also return `metadata` and `id`. Those optional fields are
accepted only after structural validation and are discarded before lookup.
They never select a file, alter a path, establish identity, authorize access,
or enter LocalFile asset ownership.

Unknown descriptor fields, malformed `metadata`, malformed `id`, unsafe
filename or subfolder values, multiple outputs, wrong output type, or a
conflicting prompt identifier fail closed.

## Result, asset, and PNG evidence

Exactly one same-origin `/view` response may supply result bytes. ComfyUI paths
are never opened directly. Before registration, the existing boundary must:

- reject redirects, proxy use, origin changes, and unexpected content type;
- enforce the 25 MB streaming limit;
- validate exactly one structurally valid PNG;
- reject truncation, trailing bytes, malformed chunks, unsafe metadata, and
  multiple selected outputs; and
- bind the result to the admitted attempt, Provider, prompt identifier,
  authorization evidence, and digest.

A successful live gate requires all of the following evidence:

- one `POST /prompt` and zero retries;
- one durable attempt in `COMPLETED` state;
- generation evidence marked ready;
- one asset registered by `LocalDurableAssetOwner`;
- strict PNG validation PASS;
- Page state changed legally from `PromptBuilt` to `Generated` through the
  existing application authority;
- no second attempt, Provider fallback, or Provider switch; and
- no new source, staged, dependency, lockfile, or repository diff caused by
  the verification.

The generated PNG and Project data are local verification artifacts, not
release artifacts. Their deletion or reuse is outside this RFC.

## Verified baseline evidence

The completed V7-05 run established this baseline:

- ComfyUI 0.40.0 listened only on `127.0.0.1:8188`;
- the device was an NVIDIA RTX 4070 Ti;
- the configured checkpoint was `animagine-xl-4.0.safetensors` and exactly
  matched a server-reported checkpoint;
- all six required node types were present as core `nodes` modules;
- one dedicated PromptBuilt Page was used;
- final live E2E used one `POST /prompt`, zero retries, and one selected PNG;
- the durable attempt completed, generation evidence was ready, asset
  registration succeeded, strict PNG validation passed, and the Page reached
  `Generated`;
- the live operation created no additional source diff; and
- independent final review reported P0 = 0, P1 = 0, and P2 = 0.

The run also showed that ComfyUI availability is an external prerequisite. If
the listener is absent, the gate stops before attempt creation or POST. If an
approved dedicated Project has already been prepared, it remains unchanged;
if the failure is found during Phase A, Project preparation does not begin.
The verifier must not start ComfyUI without separate authorization.

PR #28 (`e138cdf5b83f8da274051ae8c4028b42f4c60182`) fixed the five bounded
integration gaps and was merged into `v7-dev` as
`fd58392d919311403a32111ea7a3d2d9628d6ba9`. Its 24 required checks passed,
and both post-merge workflows (`CI` and `Push on v7-dev`) passed. The exact
eleven-file implementation allowlist is recorded in the roadmap.

## Public contract compatibility

RFC acceptance changes no public contract. The verified V7-05 corrections
remain private, additive, and compatible with:

- existing v5/v6 Python imports, calls, return shapes, and exception behavior;
- the legacy deterministic `ComfyUIImageGenerator` stub;
- mock as the default and credential-free/no-network execution;
- OpenAI V7-03 selection and generation behavior;
- `StateMachine`, `PageState`, and `WorkflowEngine` authority;
- storyboard-before-generation and `QualityChecked` before explicit approval;
- existing LocalFile formats, containment, and asset ownership;
- HTTP, Web UI, MCP, SDK, and Plugin contracts; and
- I02 independence.

No optional descriptor field, environment observation, GPU identity,
checkpoint name, generated PNG, or live-run artifact becomes public API or
persistent authority under this RFC.

## Security considerations

- Treat ComfyUI as a privileged but untrusted local service.
- Validate the loopback destination before every request and disable proxy and
  redirect behavior.
- Do not start, stop, configure, upgrade, or expose ComfyUI as part of the
  gate.
- Require core nodes only and never install or invoke custom nodes.
- Bind authorization to one exact live package and consume at most one
  Provider start.
- Keep fixed-graph preparation free of external side effects.
- Never use ComfyUI output metadata as path or identity authority.
- Persist bounded, non-secret evidence without whole Provider responses,
  arbitrary workflow JSON, environment dumps, or filesystem disclosure.
- Treat every ambiguous post-start outcome as recovery-required and never
  retry automatically.
- Keep generated artifacts local and outside release or publication evidence.

## Migration and rollback

This docs-only design requires no migration. It does not change Projects,
schemas, dependencies, commands, package metadata, or runtime behavior.

Planning rollback is to revert this RFC and the matching V7-05 roadmap entry.
Operational rollback of the already merged V7-05 correction would require a
separate, source-backed remediation plan and is not authorized here. A live
verification result must never be rolled back by deleting evidence, replaying
the attempt, or issuing a replacement generation.

## Validation plan

This design change requires:

- exact two-file allowlist review for this RFC and `docs/ROADMAP_V7.md`;
- repository-available Markdown and local-link consistency checks;
- `git diff --check`;
- proof that no code, dependency, lockfile, package metadata, version, release,
  workflow, or configuration file changed;
- architecture, compatibility, security, and authorization-boundary review;
  and
- independent read-only review with P0 = 0 and P1 = 0 before merge.

No live ComfyUI request is part of docs validation. The completed V7-05 run
and PR #28 evidence are inspected read-only; they are not replayed.

## Acceptance criteria

RFC-V7-004 is accepted only when:

1. this document and the V7-05 roadmap entry agree on scope and evidence;
2. the live gate is explicitly one Project, one Page, one attempt, one POST,
   and one PNG;
3. preflight, preparation, Provider start, observation, asset registration,
   and workflow application have distinct authority boundaries;
4. ambiguous outcomes cannot automatically retry or switch Providers;
5. ComfyUI 0.40.0 optional descriptor fields are validated and discarded as
   non-authoritative;
6. the five V7-05 corrections and exact eleven-file implementation allowlist
   are recorded without presenting them as newly authorized work;
7. public, LocalFile, workflow, OpenAI, mock, dependency, and I02 boundaries
   remain unchanged;
8. docs-only validation passes; and
9. independent review reports P0 = 0 and P1 = 0.

## Authorization gate

Acceptance freezes the V7-05 live verification design only. The completed
verification and PR #28 authorization are exhausted. This RFC does not
authorize another Project, attempt, live ComfyUI call, source remediation,
dependency change, I02 work, `main`, versioning, release, tag, publication,
Settings, force push, history rewrite, or branch deletion.

Any future live verification must present a new bounded approval package and
must stop if safe execution requires a code change or broader scope.
