# RFC-V7-002: Provider-Neutral Real Image Delivery

- Status: Accepted design; bounded V7-03 implementation complete and verified
- Target line: v7.0 Discovery (Post-LTS)
- Related roadmap item: V7-03 Provider-Neutral Real Image Delivery
- Reference Provider: OpenAI
- Implementation branch: `feat/v7-03-real-image-delivery`
- Implementation evidence: PR #23 merged into `v7-dev` at
  `b688abb88bf07e7508a806c48f86c27b6e41fa5b`; CI run #82 passed 10/10 required
  jobs; independent review reported P0/P1/P2 = 0/0/0.

## Decision boundary

The `6.0.x` line remains LTS, and `main` remains the LTS stability line. This
RFC freezes the design for the explicitly authorized V7-03 implementation on
`v7-dev`. The completed implementation stayed within the approved ten-file
allowlist and the CLI opt-in described below. It did not change the installed version,
authorize I02, or authorize a merge to `main`, release, tag, package
publication, or other deployment or distribution action.

The approved documentation change records the smallest safe path from the
existing mock generation behavior to one real generated image. That bounded
implementation received separate approval for the branch
`feat/v7-03-real-image-delivery` and was merged after the required validation
and review gates passed (see completion evidence above). Its authorization is
exhausted; this RFC does not authorize follow-up implementation.

## Problem

V7-01 and V7-02 prove that the Web UI can use the real local FastAPI,
Application, `WorkflowEngine`, StateMachine, and `LocalFileRepository` path.
The public generation adapters still use deterministic stub behavior, so that
path does not produce a real image.

The repository also contains private or future-only work for Provider
invocation, generation evidence, durable attempts, output validation, asset
registration, and recovery. Those components are useful design evidence but
do not constitute an approved public real-generation path. Some later
real-delivery components are explicitly associated with I02 and cannot be
used to bypass its separate authorization boundary.

The design must therefore deliver one real image without turning legacy stubs
into hidden network clients, changing the default behavior, storing secrets in
project data, or retrying an ambiguous external side effect.

## Goals

- Define one Provider-neutral real-image delivery boundary owned by the
  existing LocalFile durable generation chain.
- Use OpenAI as the first reference Provider while keeping the workflow and
  durable contracts Provider-neutral.
- Keep `mock` as the default for existing and new local workflows unless a
  human explicitly opts in to real generation.
- Require durable, explicit human authorization evidence before a real
  Provider attempt can start.
- Deliver exactly one prompt-only PNG for one Page through one generation
  attempt.
- Persist validated generation evidence and the resulting asset through the
  existing LocalFile ownership and containment boundaries.
- Fail closed when Provider-start outcome is ambiguous, preventing automatic
  duplicate generation and duplicate charges.
- Preserve all existing StateMachine, `WorkflowEngine`, public API, delivery,
  repository, and approval authorities.

## Non-goals

V7-03 does not include:

- reference-image or image-to-image input;
- multiple Pages, batch generation, or parallel generation;
- automatic retry after any Provider call;
- automatic Provider switching, fallback, or load balancing;
- background, scheduled, autonomous, or detached generation;
- ComfyUI real connectivity or a second real Provider;
- a change that makes `OpenAIImageGenerator` or `ComfyUIImageGenerator`
  perform network I/O;
- automatic approval or any change to the `QualityChecked` to `Approved`
  human-approval gate;
- I02 code, contracts, persistence, or authority;
- a breaking migration or intentional v5/v6 incompatibility;
- version, release, tag, package metadata, publication, repository settings,
  or `main` changes.

## Frozen design

### Provider-neutral boundary

The completed V7-03 implementation introduced or exposed one narrow
real-generation port at the existing durable generation composition boundary.
The workflow
supplies an admitted, immutable request and receives a durable result; it must
not import an OpenAI SDK type, construct a Provider in a read path, or encode
Provider-specific state transitions.

```text
Explicit local opt-in plus human authorization evidence
                         |
                         v
Existing Application and WorkflowEngine authority
                         |
                         v
LocalFile durable generation admission and attempt boundary
                         |
                         v
Provider-neutral invocation port
                         |
                         v
OpenAI reference adapter
                         |
                         v
Validated PNG, generation evidence, and LocalFile asset registration
```

The OpenAI adapter is the first reference implementation because the
repository already has private design evidence for SDK invocation, secure
input resolution, output validation, evidence construction, and LocalFile
asset registration. This choice does not make OpenAI part of the workflow
contract and does not authorize other private or future-only components for
public use.

### Default and opt-in behavior

`mock` remains the default Provider behavior. Installing, starting, opening,
or upgrading Manga Director must not cause a real Provider call. Real
generation requires all of the following for the specific attempt:

1. an explicit local real-generation opt-in;
2. a configured OpenAI reference Provider selected through the approved
   composition boundary;
3. non-empty, durable human authorization evidence identifying who authorized
   the attempt;
4. a single eligible Page in the existing `PromptBuilt` generation stage;
5. successful durable admission before Provider invocation.

Missing, malformed, conflicting, stale, or unverifiable opt-in or
authorization evidence fails closed before network use. A constant,
application-invented identity such as `local-user` is not valid evidence.

### Legacy adapters

The existing public `OpenAIImageGenerator` and `ComfyUIImageGenerator`
classes remain legacy deterministic stubs. V7-03 must not add SDK clients,
credentials, HTTP calls, environment reads, or other real-Provider behavior to
those classes. This preserves their existing imports, call forms, return
shapes, offline behavior, and tests.

Real generation is composed separately through the LocalFile durable
generation chain. The legacy stubs cannot be used as an alternate or fallback
route around durable admission, authorization evidence, or recovery rules.

### Bounded first delivery

The first implementation is limited to:

- exactly one Page;
- exactly one admitted generation attempt;
- text prompt input only;
- exactly one PNG output candidate;
- validated bytes within the existing configured output limit;
- one durable evidence record and one LocalFile-owned asset registration.

A response containing no valid PNG, more than one selected output, unsupported
media, malformed encoding, inconsistent evidence, or unsafe asset metadata
fails closed. The implementation must not silently choose a reference image,
start a second attempt, or switch Providers.

### Durable execution and unknown outcomes

Durable admission and attempt identity must be persisted before the Provider
call opportunity is consumed. The same attempt identity can consume that call
opportunity at most once.

If the process loses certainty after Provider start, including timeout,
connection loss, process termination, malformed response, or a persistence
failure that makes the external outcome ambiguous, the Page or attempt enters
the existing fail-closed recovery-required path. The system must not
automatically re-invoke OpenAI, create a replacement attempt, retry with
another Provider, or claim that generation did not occur.

Recovery may inspect and reconcile durable evidence, but a future recovery
execution that can cause another external side effect requires a separately
specified and authorized path. This RFC does not promote the private future
submission/result journals to a public recovery API.

### Workflow and approval authority

`StateMachine` remains the sole Page-transition authority, and
`WorkflowEngine` remains the execution authority. V7-03 does not add, remove,
skip, reverse, or rename a state. The existing transition from `PromptBuilt`
to `Generated` may occur only after the durable generation result is accepted
and applied through existing authorities.

Storyboard persistence still precedes image generation. Generation does not
imply quality acceptance: the Page must still complete the existing quality
review, persist `QualityChecked`, and receive separate explicit human approval
before `Approved` is legal.

## Secret boundary

Provider credentials are resolved only at execution time through the approved
secret boundary. Raw secrets, tokens, authorization headers, or equivalent
credential material must never be stored in:

- Project, Page, storyboard, prompt, asset, or generation metadata;
- application configuration files or Provider configuration records;
- LocalFile repository data, durable attempt records, evidence, journals, or
  logs;
- HTTP DTOs, errors, diagnostics, traces, or user-visible output.

Configuration may store a non-secret Provider identifier and non-secret model
or output settings when separately approved. Secret presence may be checked
without returning, hashing into public evidence, or persisting the secret.
Tests and default workflows must run without credentials or external network.

## Affected public contracts

RFC acceptance changes no public contract. The completed V7-03 implementation
was additive and preserved:

- v5/v6 Python imports, call forms, return shapes, and exception behavior;
- CLI commands, arguments, defaults, and exit semantics;
- MCP tools, schemas, imports, and local stdio behavior;
- existing HTTP DTOs and Web UI behavior unless explicitly included in the
  later implementation allowlist;
- `OpenAIImageGenerator` and `ComfyUIImageGenerator` stub behavior;
- `StateMachine`, `PageState`, and transition rules;
- `WorkflowEngine` one-Page execution semantics;
- repository ports, LocalFile formats, root containment, and path safety;
- existing mock Provider determinism and provider-free test execution.

No private, future-only, or I02-prefixed module becomes a supported public API
because it is discussed or reused internally by a later implementation.

## Compatibility analysis

The design is backward compatible because real generation is optional,
explicit, and composed beside the unchanged default mock path. Provider SDK
types and credentials remain behind an infrastructure boundary, and existing
public stubs retain their behavior.

Compatibility requires observable proof that an environment with no OpenAI
credential behaves exactly as before unless real generation is explicitly
requested. Existing persisted Projects must open and continue to use mock
generation without migration. A `RECOVERY_REQUIRED` record must fail closed
without changing Page state or triggering another Provider call.

Any required change to a frozen public contract, existing LocalFile schema,
StateMachine transition, default Provider selection, or I02 component is a
scope expansion. Work must stop and return to design review rather than
silently widening V7-03.

## Alternatives considered

### Make the legacy OpenAI adapter real

Rejected. Existing callers rely on its deterministic stub behavior. Adding
network and credential effects would be a silent compatibility break and
would permit calls outside the durable generation boundary.

### Use ComfyUI as the first reference Provider

Deferred. ComfyUI is a plausible later local Provider, but its current adapter
does not provide the same repository-backed invocation and evidence foundation
as the OpenAI design path. Adding a second real Provider is outside the first
delivery.

### Automatically retry an ambiguous attempt

Rejected. The external request may already have been accepted, so retrying can
duplicate output and cost. Recovery-required is the safe default.

### Reuse I02 real-delivery components

Rejected for V7-03. I02 has a separate explicit authorization boundary. This
RFC must remain independently implementable without importing I02 authority or
treating I02 work as implicitly approved.

### Store an API key in Project or Provider configuration

Rejected. Project data is durable and portable and is not a secret store.
Persisting credentials there would create disclosure, backup, and accidental
publication risks.

## Migration and rollback

No data migration is authorized. Existing Projects and mock workflows require
no conversion.

Before any release, operational rollback is to disable the explicit
real-generation composition and return to the unchanged mock default. A
failed or disabled real Provider must not trigger migration, automatic
fallback, or deletion of accepted assets or evidence. Ambiguous attempts and
their recovery evidence remain preserved for diagnosis; rollback must not
erase or replay them.

Planning-only rollback consists of reverting this RFC and its V7-03 roadmap
entry. If a later implementation proposes a new durable format, it must define
forward and reverse compatibility in a separately approved scope before that
format is written.

## Security considerations

- Resolve secrets only through the execution-time secret boundary and redact
  them from all persistence and diagnostics.
- Permit network use only after explicit opt-in, durable admission, and human
  authorization validation.
- Bind the feature to the existing local-only delivery boundary; do not add
  remote exposure, OAuth, JWT, or a cloud control plane.
- Validate prompt size and Provider configuration before invocation without
  logging sensitive prompt or credential material beyond existing policy.
- Decode and validate the returned PNG before asset registration; enforce the
  existing byte limit and reject unsupported, malformed, or multiple selected
  outputs.
- Preserve LocalFile root containment, safe names, atomic writes, and
  symlink/reparse-point protections.
- Record stable, non-secret Provider, model, attempt, authorization, and output
  evidence sufficient for audit without persisting SDK responses or secrets.
- Prevent duplicate invocation across restart, concurrency, refresh, and
  ambiguous Provider outcomes.
- Keep default, test, and package verification paths offline and credential
  free.

## Validation plan

The approved implementation provided executed evidence for:

- exact changed-file allowlist review and `git diff --check`;
- default mock behavior with no credential and no external network;
- explicit opt-in and human authorization evidence admission, including
  missing, blank, forged, stale, conflicting, and replayed evidence failures;
- one Page, one attempt, prompt-only input, and one PNG output enforcement;
- proof that the Provider is called only through the LocalFile durable
  generation chain;
- at-most-once Provider-start behavior across restart, refresh, concurrency,
  timeout, and process-loss tests;
- `RECOVERY_REQUIRED` behavior with no automatic retry, replacement attempt,
  or Provider switch;
- PNG decoding, byte limit, malformed/multiple-output rejection, safe asset
  registration, and evidence persistence tests;
- secret non-persistence checks across Project/configuration/metadata,
  LocalFile data, evidence, journals, logs, HTTP responses, and diagnostics;
- unchanged legacy OpenAI and ComfyUI stub contract tests;
- StateMachine, `WorkflowEngine`, storyboard-before-generation,
  `QualityChecked`, and explicit approval regressions;
- CLI, MCP, HTTP, Web UI, Repository, SDK, Plugin, and public-import
  compatibility checks applicable to the final diff;
- LocalFile path-containment and Windows security regression;
- Python lint, type checking, focused tests, and full applicable regression;
- Web lint, type checking, tests, build, and browser gates if Web files are in
  the separately approved implementation scope;
- dependency and security audit evidence for any separately approved SDK or
  dependency change;
- package and public-contract verification if package contents are affected.

The completed implementation remained within its exact ten-file allowlist and
passed the applicable local, CI, security, package, compatibility, and
independent read-only review gates before merge to `v7-dev` (see completion
evidence above).

## Documentation impact

The bounded implementation synchronizes only this RFC, `ROADMAP_V7.md`, the
README CLI guidance, and secret-management guidance. Release notes, migration
guides, version metadata, and publication material remain outside this RFC.

## Acceptance criteria

This RFC was accepted when reviewers confirmed that it:

- selects OpenAI only as the first reference Provider while keeping the
  boundary Provider-neutral;
- keeps `mock` as the default and requires explicit real-generation opt-in;
- leaves the legacy OpenAI and ComfyUI adapters as non-network stubs;
- permits real generation only through the LocalFile durable generation chain;
- excludes secrets from Project, configuration, metadata, persistence, and
  diagnostics;
- requires durable human authorization evidence for the specific attempt;
- bounds the first delivery to one Page, one attempt, prompt-only input, and
  one PNG;
- excludes reference images, batch, automatic retry, Provider auto-switching,
  and background generation;
- prohibits automatic regeneration after an ambiguous Provider start;
- preserves StateMachine, `WorkflowEngine`, quality-review, and approval
  authority;
- remains independent of I02 and changes no public contract by acceptance;
- defines compatibility, rollback, security, and executable validation gates;
  and
- records the completed, separately approved V7-03 implementation and does not
  authorize follow-up implementation, release, version, tag, publication,
  Settings, branch deletion, force push, or `main` change.
