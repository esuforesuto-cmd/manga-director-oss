# v7 Development Roadmap

## Planning baseline

The `6.0.x` line remains LTS, and `main` remains the LTS stability line. v7.0
Discovery is the Post-LTS development line for new feature proposals that do
not belong in v6 LTS maintenance. The v7 designation separates new feature
work from v6 LTS; it does not signal an intention to introduce breaking
changes.

This roadmap is a planning artifact. It does not change the installed version,
authorize a release, change package metadata, or authorize tag or package
publication. Work enters `main` only through its separately approved and
validated change process.

## Epic 1 — Local Workflow Delivery

### Objective

Connect the existing Web UI to the current Manga Director workflow through a
safe, optional, local HTTP delivery boundary while retaining all established
Domain, Application, workflow, repository, and delivery authorities.

### Required invariants

- `StateMachine` remains the sole transition authority.
- `WorkflowEngine` remains the execution authority.
- Each execution processes exactly one Page.
- Storyboard persistence precedes image generation.
- Approval requires persisted `QualityChecked` state and explicit human
  approval evidence.
- Workflow and delivery remain Provider-neutral.
- v5/v6 Python, CLI, MCP, Web UI, Repository, SDK, Plugin, and StateMachine
  compatibility is preserved.
- `LocalFileRepository` security and configured-root containment are preserved.

### Initial non-goals

- cloud or remote exposure;
- OAuth, JWT, or an internet-facing API;
- automatic approval or automatic retry;
- autonomous or parallel execution;
- `StateMachine` changes;
- automatic Provider switching;
- Marketplace network behavior;
- a Project DELETE API;
- I02;
- a breaking migration;
- version, release, package metadata, tag, or publication changes.

## V7-01 — Workflow HTTP Adapter

### Outcome

Provide the existing Web UI with an optional loopback-only HTTP adapter that
maps dedicated HTTP DTOs to a transport-neutral Application service. The
Application service delegates workflow execution to the existing
`WorkflowEngine` and persistence to existing repository ports. HTTP must not
own transitions, call Agents directly, select Providers, or change CLI/MCP
contracts.

### Inputs

- [RFC-V7-001: Local Workflow HTTP Delivery](RFC_V7_001_LOCAL_WORKFLOW_HTTP_DELIVERY.md)
- the existing Web UI client and presentation contracts;
- current Workflow, StateMachine, Repository, CLI, and MCP contracts;
- merged PR #17 as the verified V7-01 implementation evidence.

### Completion evidence

PR #17, `feat(api): add local workflow HTTP adapter`, was merged into `v7-dev`
on 2026-10-13 as merge commit `097a80d786f494063492eaa871deef6bbf5ab169`.
The retargeted PR passed all required Python, Windows, Web, security, package,
compatibility, and documentation checks, and its independent review found no
P0 or P1 issues. `main` remained unchanged at
`b0291437af05fe53454843ba95fdf88216700f7c`; no version, release, tag,
publication, branch-setting, or I02 change was included.

### Acceptance criteria

- The server is local-only and cannot be configured for remote exposure in the
  initial scope.
- Dedicated HTTP DTOs prevent Domain models from becoming the wire contract.
- Read endpoints do not save Repository data, transition state, execute Agents,
  or construct Providers.
- Mutating endpoints preserve the one-Page execution and transition rules.
- Approval requires `QualityChecked` and explicit human approval evidence.
- No Project DELETE, auto-approve, auto-retry, autonomous execution, parallel
  execution, Provider auto-switching, Marketplace network, or I02 surface is
  introduced.
- Existing Python, CLI, MCP, Web UI, Repository, SDK, Plugin, StateMachine, and
  LocalFile compatibility/security regressions pass.
- Applicable Python and Web quality checks, full regression, security checks,
  package checks, and `git diff --check` pass.
- The final implementation diff and documentation match an explicitly
  authorized v7 allowlist.

### Authorization gate

Acceptance of RFC-V7-001 authorizes an implementation proposal only. V7-01
implementation, merge, versioning, release, tag, and publication decisions are
separate gates. No roadmap entry authorizes I02.

## V7-02 — Real Local Delivery End-to-End Gate

### Planning status

Complete and verified on PR #20. This entry remains the bounded Issue
Specification for V7-02 implementation and validation. It does not authorize
release or publication.

### Completion evidence

PR #20, with final head `7d0034a2dad46c6ff982d03104d32d935d5db796`,
was merged into `v7-dev` as merge commit
`ad671b63a4135997ffc41e8ab95bb8a681668980`. CI run #69 passed all ten
required jobs, including the real local delivery Playwright gate on Windows,
both Windows full-regression jobs, Python and Web quality gates, security
checks, and package verification. Independent review reported P0 = 0, P1 = 0,
and P2 = 0. The implementation changed exactly the approved seven-file
allowlist; `package-lock.json` and `src/` remained unchanged. `main` remained
unchanged at
`b0291437af05fe53454843ba95fdf88216700f7c`, and no version, release, tag,
publication, Settings, branch deletion, force-push, or I02 change was included.

### Objective

Prove that the existing Web UI and the V7-01 loopback HTTP adapter work
together through the real local Application, `WorkflowEngine`, StateMachine,
and `LocalFileRepository` boundaries in one deterministic end-to-end quality
gate. The gate must add verification only, not new product behavior.

### Scope

- add a dedicated browser end-to-end mode that starts the real
  `manga-director api serve` command and the existing Next.js Web UI on
  loopback interfaces;
- use an isolated temporary configuration, repository root, and the existing
  mock Providers so the scenario needs no credentials or external network;
- exercise one Page from Project creation through `QualityChecked` and
  explicit human approval, using only actions supplied by the real API;
- verify the persisted approved result after a browser refresh or a fresh read;
- run the real-delivery browser scenario as a required Windows CI gate,
  matching the current durable LocalFile execution platform, while retaining
  the existing mock-API browser test for fast presentation feedback;
- document the local command, isolation behavior, and failure diagnostics.

### Inputs

- completed V7-01 Workflow HTTP Adapter and its accepted invariants;
- [RFC-V7-001: Local Workflow HTTP Delivery](RFC_V7_001_LOCAL_WORKFLOW_HTTP_DELIVERY.md);
- the existing FastAPI CLI entry point, Web API client, Playwright setup,
  `LocalFileRepository`, and mock Provider implementations;
- the current Python, Web, LocalFile security, compatibility, and package
  quality gates.

### Outputs

- a deterministic real-API Playwright scenario separate from the mock-API
  scenario;
- minimal process and temporary-state orchestration owned by test tooling;
- a required CI invocation for the real local delivery gate;
- synchronized Web UI, HTTP API, and troubleshooting documentation.

### Acceptance criteria

- The browser communicates with the real FastAPI adapter; the test does not
  substitute `web/e2e/mock-api.mjs` for this scenario.
- The API and Web UI bind only to documented loopback addresses and use an
  isolated temporary repository root.
- The scenario creates exactly one Page, follows API-provided actions without
  skipping or reversing a state, and persists storyboard data before image
  generation.
- Approval is unavailable before persisted `QualityChecked`, requires a
  non-empty human identity, and produces an `Approved` Page that remains
  observable after refresh or a fresh read.
- The scenario uses existing mock Providers and performs no external model,
  Marketplace, or credentialed network request.
- Test orchestration terminates child processes and removes temporary test
  state on success and failure.
- The existing mock-API browser test remains available and passes.
- No runtime endpoint, HTTP DTO, Domain model, StateMachine rule, CLI or MCP
  contract, Provider selection rule, or public import changes.
- No new runtime or development dependency, Project DELETE, auto-approval,
  auto-retry, parallel execution, remote exposure, or I02 surface.
- The implementation stays within an approved allowlist and passes the
  required Python, Web, browser, compatibility, security, package, and
  whitespace checks.

### Out of scope

- new workflow actions, endpoints, DTO fields, or Web UI features;
- a combined production launcher or installer for the API and Web UI;
- cloud deployment, remote access, authentication, OAuth, or JWT;
- Provider changes, live model calls, automatic Provider switching, or
  Marketplace behavior;
- Project deletion, automatic approval, automatic retry, autonomous or
  parallel execution;
- StateMachine, persistence-format, version, release, tag, package metadata,
  publication, default-branch, ruleset, or I02 changes.

### Dependencies

- V7-01 remains complete and unchanged on `v7-dev`.
- Existing optional API and Web development dependencies are sufficient; a
  dependency or lockfile change requires a revised plan and separate review.
- The CI runner can install the already-declared Playwright Chromium runtime.

### Validation

- `ruff check .`;
- the repository's current Linux and Windows `mypy` gates;
- focused HTTP/Application tests and the full applicable `pytest` regression;
- `npm run lint`, `npm run typecheck`, `npm run test`, and `npm run build`;
- existing mock-API Playwright E2E and the new real-API Playwright E2E;
- LocalFile path-containment and Windows LocalFile security regression;
- `pip-audit --strict .` and `npm audit --omit=dev --audit-level=high`;
- package/public-contract checks already required by CI;
- exact changed-file allowlist review and `git diff --check`.

### Estimated complexity

Medium. The product behavior is unchanged, but deterministic startup,
readiness, cleanup, temporary persistence, and CI process ownership cross the
Python and Web test boundaries.

### Architecture notes

The new orchestration belongs to test tooling only. Production Web components
continue to call the typed REST client; FastAPI remains a Presentation adapter;
the Application service, `WorkflowEngine`, StateMachine, repository ports, and
Provider composition retain their existing authority. The real-delivery test
must invoke public local entry points instead of importing Web code into Python
or duplicating workflow decisions in its harness.

### Authorization gate

The approved V7-02 scope authorizes the bounded implementation, commit, push,
pull request, CI, read-only review, in-scope P0/P1 remediation, and merge to
`v7-dev` when every required condition passes. `main`, versioning, release,
tag, publication, branch deletion, force-push, settings, and I02 remain out of
scope.

## V7-03 — Provider-Neutral Real Image Delivery

### Implementation status

Complete and verified on PR #23. The design remains frozen by
[RFC-V7-002: Provider-Neutral Real Image Delivery](RFC_V7_002_PROVIDER_NEUTRAL_REAL_IMAGE_DELIVERY.md),
and the implementation remains bounded by its approved ten-file allowlist.

### Completion evidence

PR #23 was merged into `v7-dev` as merge commit
`b688abb88bf07e7508a806c48f86c27b6e41fa5b`. CI run #82 passed all ten
required jobs. Independent review reported P0 = 0, P1 = 0, and P2 = 0. The
feature branch `feat/v7-03-real-image-delivery` was retained. `main` remained
unchanged at `b0291437af05fe53454843ba95fdf88216700f7c`.

The completed implementation changed exactly this approved ten-file
allowlist:

1. `README.md`
2. `docs/RFC_V7_002_PROVIDER_NEUTRAL_REAL_IMAGE_DELIVERY.md`
3. `docs/ROADMAP_V7.md`
4. `docs/SECRETS_CREDENTIAL_MANAGEMENT.md`
5. `src/manga_director/cli/app.py`
6. `src/manga_director/production/next_generation_local_durable_asset_owner.py`
7. `src/manga_director/workflow/localfile_real_image_generation.py`
8. `tests/integration/test_cli.py`
9. `tests/test_localfile_real_image_generation.py`
10. `tests/test_next_generation_local_durable_asset_owner.py`

### Objective

Deliver one real, prompt-only PNG for one Page through the existing LocalFile
durable generation chain without changing the default mock behavior or
weakening workflow, persistence, security, compatibility, or human-approval
authority. OpenAI is the first reference Provider; the boundary remains
Provider-neutral.

### Bounded scope

- retain `mock` as the default and require explicit opt-in for every real
  generation path;
- require durable human authorization evidence for the specific generation
  attempt before network use;
- permit one eligible Page, one admitted attempt, prompt-only input, and one
  validated PNG output;
- invoke the OpenAI reference adapter only through the existing LocalFile
  durable generation chain;
- keep legacy `OpenAIImageGenerator` and `ComfyUIImageGenerator` behavior as
  deterministic, non-network stubs;
- resolve credentials only at execution time through the approved secret
  boundary and never store them in Project, configuration, metadata,
  persistence, evidence, logs, or diagnostics;
- persist non-secret generation evidence and register the validated asset
  through existing LocalFile containment and ownership boundaries;
- fail closed without automatic regeneration when Provider start or result is
  ambiguous;
- preserve `StateMachine`, `WorkflowEngine`, storyboard-before-generation,
  `QualityChecked`, and explicit approval authority.

### Out of scope

- reference images, image-to-image input, batch or parallel generation;
- automatic retry, replacement attempts, Provider fallback or auto-switching;
- background, scheduled, autonomous, or detached generation;
- ComfyUI real connectivity or another real Provider;
- public activation of private/future-only recovery components;
- I02 or use of I02 authority, contracts, persistence, or implementation;
- public API, StateMachine, existing LocalFile format, default Provider,
  dependency, version, release, tag, publication, Settings, `main`, or branch
  deletion changes without a separately approved scope.

### Compatibility

The implementation is additive and opt-in, keeps existing credential-free
workflows offline, and
must preserve Python, CLI, MCP, HTTP, Web UI, Repository, SDK, Plugin,
StateMachine, `WorkflowEngine`, legacy adapter, and mock Provider behavior.
Existing Projects require no migration. Any need to change a frozen contract,
LocalFile schema, transition, default, or I02 component is a scope expansion
and stops V7-03 implementation pending a new decision.

### Validation

- exact implementation allowlist and `git diff --check`;
- default mock/no-credential/no-network regression;
- explicit opt-in and human authorization admission and rejection cases;
- one-Page/one-attempt/prompt-only/single-PNG enforcement;
- at-most-once Provider start across restart, concurrency, timeout, and process
  loss, with `RECOVERY_REQUIRED` and no automatic retry or Provider switch;
- PNG, byte-limit, evidence, asset-registration, LocalFile containment, and
  secret non-persistence security tests;
- unchanged legacy OpenAI/ComfyUI stubs and public compatibility surfaces;
- StateMachine, `WorkflowEngine`, quality, approval, focused, full regression,
  lint, type-check, security/audit, package, and browser gates applicable to
  the separately approved final diff.

The implementation is limited to its approved ten-file allowlist. It requires
exact allowlist review, `git diff --check`, applicable local and CI gates, and
independent review with P0 = 0 and P1 = 0 before merge to `v7-dev`.

### Approval state

V7-03 is complete. Its prior authorization is exhausted by PR #23 and does not
authorize follow-up implementation. It does not authorize I02, `main`,
versioning, release, tag, publication, Settings, force push, or branch
deletion.

## V7-04 — ComfyUI Local Provider

### Implementation status

Complete and verified on PR #26. The design remains frozen by
[RFC-V7-003: ComfyUI Local Provider Delivery](RFC_V7_003_COMFYUI_LOCAL_PROVIDER.md).
The implementation remains bounded by its approved twelve-file allowlist.

### Completion evidence

PR #26 was merged into `v7-dev` as merge commit
`abd5a21a2597cb51286b666b23298b5f47450094`. Post-merge CI run #95 passed all
ten required jobs, and CodeQL run #19 passed all three jobs. Independent review
reported P0 = 0, P1 = 0, and P2 = 0. The feature branch
`feat/v7-04-comfyui-local-provider` was retained. `main` remained unchanged at
`b0291437af05fe53454843ba95fdf88216700f7c`.

The completed implementation changed exactly this approved twelve-file
allowlist:

1. `README.md`
2. `docs/ROADMAP_V7.md`
3. `src/manga_director/cli/app.py`
4. `src/manga_director/production/next_generation_comfyui_fixed_workflow.py`
5. `src/manga_director/production/next_generation_comfyui_output_asset_registration.py`
6. `src/manga_director/production/next_generation_comfyui_provider_adapter.py`
7. `src/manga_director/workflow/localfile_comfyui_real_image_generation.py`
8. `tests/integration/test_cli.py`
9. `tests/test_localfile_comfyui_real_image_generation.py`
10. `tests/test_next_generation_comfyui_fixed_workflow.py`
11. `tests/test_next_generation_comfyui_output_asset_registration.py`
12. `tests/test_next_generation_comfyui_provider_adapter.py`

### Objective

Implement the smallest safe application of the Provider-neutral LocalFile
durable real-generation boundary completed by V7-03 to a local ComfyUI server
as a second reference Provider, without changing existing public, workflow,
persistence, or approval contracts.

### Frozen first-slice direction

- keep the legacy public `ComfyUIImageGenerator` as a deterministic,
  non-network stub and keep `mock` as the default;
- make future activation CLI-only and explicit, equivalent to
  `--real-provider comfyui`, with durable human authorization evidence;
- default to `http://127.0.0.1:8188` and reject remote/LAN, DNS, cloud, proxy,
  redirect, credential-bearing, wildcard, and unsupported endpoint forms;
- use a Manga Director-owned, fixed, validated, core-node-only workflow graph;
- exclude arbitrary workflow JSON, custom nodes, third-party node packages,
  embedded scripts, node installation, and model download;
- permit one Page, one admitted attempt, prompt-only input, and exactly one
  PNG;
- treat `POST /prompt` as Provider start, observe the same `prompt_id` through
  bounded `/history/{prompt_id}` polling, and retrieve bytes through
  same-origin `/view` without requiring WebSocket support;
- never read or trust a ComfyUI output filesystem path directly;
- validate strict PNG structure and the existing 25 MB byte limit before
  `LocalDurableAssetOwner` registration;
- use `RECOVERY_REQUIRED` for ambiguous submission or result outcomes and
  prohibit automatic POST resubmission, replacement attempts, fallback, or
  Provider switching;
- keep ComfyUI, models, checkpoints, and custom nodes outside the Manga
  Director repository and package; and
- prefer the standard library or already-declared runtime dependencies; this
  design authorizes no dependency or lockfile change.

### Compatibility and exclusions

V7-04 must preserve `StateMachine`, `WorkflowEngine`, one-Page execution,
storyboard-before-generation, `QualityChecked` before explicit approval,
Provider neutrality, existing LocalFile schema and security, mock defaults,
OpenAI V7-03 behavior, HTTP, Web UI, MCP, SDK, Plugin, and v5/v6/public
compatibility.

I02 is completely independent and out of scope. No I02 authority, import,
persistence, contract, or implementation may be used. If a future
implementation proves I02 necessary, V7-04 becomes `BLOCKED` pending separate
approval instead of expanding scope.

Reference images, image-to-image input, batch, parallel, background,
scheduler, automatic retry, fallback, auto-switch, remote exposure,
authentication, public API changes, versioning, release, tag, publication,
Settings, `main`, force push, and branch deletion are out of scope.

### Validation

Implementation validation passed the 72-test V7-04 focused set, Ruff,
mypy across 302 source files, a 124-test OpenAI/public/v6/HTTP/MCP/SDK/Plugin
compatibility set, and the 3,051-test full suite (3,037 passed, 14 skipped).
The focused set covers loopback parsing, disabled proxies, redirect rejection,
read-only preflight, exact checkpoint and core-node checks, fixed graph,
single submission, bounded polling, recovery-required ambiguity, strict PNG,
25 MB streaming limits, unsafe output metadata, asset ownership, durable
attempt ordering, default mock, and OpenAI selection. No dependency, lockfile,
public export, StateMachine, LocalFile schema, HTTP, Web, MCP, SDK, Plugin, or
I02 change was required.

### Authorization gate

V7-04 is complete. Its prior authorization is exhausted by PR #26 and does not
authorize follow-up implementation or a live ComfyUI call. It does not
authorize I02, `main`, dependency changes, versioning, release, tag,
publication, Settings, force push, or branch deletion.

## V7-06 — Human Visual QA and Approval Readiness

### Planning status

Design approved and frozen by
[RFC-V7-004: Human Visual QA and Approval Readiness](RFC_V7_004_HUMAN_VISUAL_QA_APPROVAL_READINESS.md).
The exact three-file V7-06 implementation is complete and verified. PR #31 was
merged into `v7-dev` at `7c1d7d993e2c94dfd8c716ba7f6210c2b3117a42` after
independent review and all required gates passed. It remains an internal,
read-only advisory contract and authorizes no execution or live generation.

### Objective

Define the smallest deterministic, read-only evidence flow from one validated
generation result through explicit human visual QA to an advisory
approval-readiness status, while preserving the existing
`QualityChecked`-to-explicit-approval boundary.

### Inputs

- the verified generation-evidence and registered-asset chain on `v7-dev`,
  including the V7-05 hardening merged by PR #28;
- one existing Project and Page, one exact generation attempt, one registered
  PNG asset, and one provenance reference;
- the existing read-only Visual Continuity QA report and checklist;
- caller-supplied human visual judgment with reviewer identity and rationale;
- the current persisted Page state; and
- existing `StateMachine`, `WorkflowEngine`, LocalFile containment,
  quality-review, and explicit-approval contracts.

### Outputs

- one advisory `ready`, `needs_review`, or `blocked` status;
- deterministic ordered findings and missing prerequisites;
- exact logical references for the Page, attempt, asset, provenance, and human
  review evidence; and
- a human approval hand-off that performs no state transition.

### Frozen behavior

- use one Page and one exact attempt/asset/provenance chain;
- validate generation evidence and asset binding before visual-review
  readiness;
- retain existing automated Visual Continuity QA as advisory checklist input,
  never as a substitute for human image inspection;
- require a named human to record visual judgment and rationale for the exact
  selected output;
- derive statuses with `blocked` taking precedence over `needs_review`, and
  `needs_review` taking precedence over `ready`;
- use `blocked` for integrity, binding, safety, ambiguity, or explicit human
  stop findings;
- use `needs_review` for incomplete human inspection, unresolved
  non-blocking evidence, revision requests, or a Page not yet persisted as
  `QualityChecked`;
- use `ready` only when the exact evidence chain is valid, human visual
  review is complete and acceptable, the Page is persisted as
  `QualityChecked`, and no finding remains;
- leave a `ready` Page at `QualityChecked`; only the existing separate
  explicit `approve` action with human identity may request `Approved`;
- fail closed without regeneration, retry, fallback, asset mutation, approval,
  or notification; and
- preserve deterministic ordering and logical references without current-time,
  filesystem-order, network, or Provider dependence.

### Acceptance criteria

- the documented sequence is generation evidence → Visual QA → human judgment
  → approval readiness;
- all three readiness statuses have deterministic, fail-closed definitions;
- generation success, automated QA, and `ready` are explicitly not approval;
- the existing Page state sequence is unchanged, with persisted
  `QualityChecked` and separate explicit human approval required before
  `Approved`;
- one-Page scope and exact attempt/asset/provenance correlation are mandatory;
- no reviewer identity, evidence version, attempt, asset, or policy is inferred
  or auto-selected;
- no public API, DTO, persistence schema, dependency, workflow, Provider,
  LocalFile, StateMachine, or compatibility contract changes;
- I02 remains fully independent; and
- the exact three-file implementation allowlist, focused and full regression,
  lint, type-check, security/audit, package, independent review, required CI,
  CodeQL, and post-merge checks pass with no P0/P1 finding.

### Compatibility and exclusions

V7-06 preserves Python, CLI, HTTP, Web UI, MCP, SDK, Plugin, Repository,
Provider, generation-evidence, LocalFile, `StateMachine`, `WorkflowEngine`,
v5, v6, and public API compatibility. No migration is required.

I02 remains completely independent and out of scope. The V7-06 implementation
adds one internal advisory module and its focused tests. It does not authorize
public exports, persistence, image or asset access, live generation, Project
or Page mutation, approval execution, dependencies, lockfiles, package
metadata, versioning, `main`, release, tag, publication, Settings, force push,
history rewriting, or branch deletion.

### Validation

- exact allowlist:
  `src/manga_director/production/next_generation_human_visual_qa_approval_readiness.py`,
  `tests/test_next_generation_human_visual_qa_approval_readiness.py`, and
  `docs/ROADMAP_V7.md`;
- focused deterministic status, precedence, binding, security, and
  non-mutation tests;
- related generation-binding, Visual QA, human-decision, StateMachine,
  workflow, and V6 LTS regressions;
- lint, type-check, security/audit, package, and `git diff --check` gates;
- zero dependency, lockfile, workflow, package-metadata, version, or settings
  diff;
- architecture, StateMachine, approval-boundary, LocalFile-security, and
  public-compatibility review;
- independent review with P0 = 0 and P1 = 0; and
- required hosted CI, CodeQL, and post-merge verification.

### Authorization gate

V7-06 is complete. Its implementation authorization was exhausted by PR #31
and does not authorize follow-up changes, a fourth file, public API,
StateMachine, WorkflowEngine, persistence, dependency, Provider, delivery
surface, live operation, I02, `main`, release, tag, Settings, force push,
history rewriting, or branch deletion.

## V7-07 — Safe Local Generated Asset Presentation

### Planning status

Design approved and frozen by
[RFC-V7-005: Safe Local Generated Asset Presentation](RFC_V7_005_SAFE_LOCAL_GENERATED_ASSET_PRESENTATION.md).
The exact fifteen-file V7-07 implementation is complete and verified. PR #33
was merged into `v7-dev` at `9aad271fd8ff66d7516e2f066f55d2a0d62d4fbf`
after independent review and all required gates passed, including the final
post-merge Windows 3.11 rerun.

### Objective

Define the smallest fail-closed, read-only presentation path that lets the
existing loopback Web UI display the exact registered PNG already bound to one
existing Page, without accepting filesystem authority from the caller or
changing workflow, Provider, review, or approval behavior.

### Inputs

- one existing Project and Page identified only by the local route;
- the Page's persisted `Generated` logical `output_asset_id`;
- the existing durable generation/application binding for the same Page,
  attempt, asset, provenance, media type, digest, and byte length where
  recorded;
- the matching `LocalDurableAssetOwner` registry row and contained private
  asset; and
- the existing loopback-only workflow HTTP and Web delivery boundary.

### Outputs

- one complete, revalidated PNG response for the exact Page-bound registered
  asset;
- fixed `Content-Type: image/png`, `Cache-Control: no-store`, and
  `X-Content-Type-Options: nosniff` headers; or
- a redacted fail-closed error with no image bytes, path, storage name, digest,
  or Provider metadata disclosure.

### Frozen behavior

- use one additive loopback-only `GET` equivalent to
  `/projects/{project_id}/pages/{page_number}/generated-asset`;
- accept only validated Project identity and positive Page number, with no
  request body, query-selected output, caller asset ID, attempt, Provider,
  digest, path, storage name, root, URI, or URL;
- resolve exactly Page → persisted logical generated asset → durable generation
  binding → one exact owner-registry row → one exact contained file;
- keep the HTTP adapter presentation-only and delegate coordination to a
  transport-neutral private Application read service;
- keep `LocalDurableAssetOwner` authoritative for registry, private storage
  naming, configured-root containment, file identity, byte limit, and digest;
- open existing registry and asset state read-only, without create-on-read,
  repair, registration, or migration;
- revalidate media type, the existing 25 MB limit, SHA-256 digest, and strict
  PNG structure on the same opened bytes returned to the browser;
- return `image/png` with `Cache-Control: no-store`, disclose no filesystem
  path or storage name, and emit no redirect or cache validator;
- reject ambiguity, duplicates, legacy path artifacts, unsafe file identity,
  binding mismatch, corruption, malformed PNG, and partial reads without
  falling back to another asset;
- perform no outbound request and prohibit remote, LAN, wildcard, DNS, proxy,
  redirect, Provider, and arbitrary-file behavior;
- perform no mutation, workflow execution, state transition, quality action,
  review persistence, readiness calculation, or approval; and
- remain completely independent of I02.

### Acceptance criteria

- only the exact Page-bound registered PNG can produce a successful response;
- the caller cannot select or disclose a path, storage name, asset, attempt,
  Provider, digest, root, or URL;
- Page, durable binding, owner registry, media type, digest, and opened bytes
  must agree exactly;
- the exact returned bytes pass containment, ordinary-file, byte-limit,
  SHA-256, and strict PNG revalidation;
- the response is loopback-only `GET`, `image/png`, and
  `Cache-Control: no-store`, with no redirect or storage disclosure;
- no Project, Page, registry, asset, evidence, review, readiness, or approval
  mutation occurs;
- no Provider, generation, retry, fallback, remote fetch, DNS, proxy,
  StateMachine, `WorkflowEngine`, or I02 operation occurs;
- current Python, CLI, HTTP JSON DTO, Web workflow, MCP, SDK, Plugin,
  Repository, LocalFile, Provider, V7-06, v5/v6, and public compatibility is
  preserved;
- no dependency, lockfile, persistence schema, package metadata, version,
  release, Settings, or `main` change is authorized; and
- the exact two-file docs allowlist, Markdown links, `git diff --check`,
  independent review, required CI, CodeQL, and post-merge checks pass with no
  P0 or P1 finding.

### Compatibility and exclusions

This docs-only design changes no current contract. A separately approved
implementation may add only the bounded loopback binary presentation route and
private composition described by RFC-V7-005. Existing routes and DTOs, public
Python imports, CLI, MCP, SDK, Plugin, Repository and LocalFile formats,
Providers, `StateMachine`, `WorkflowEngine`, Page states, generation,
`QualityChecked`, V7-06 readiness, and explicit approval remain unchanged.

No migration is required. Arbitrary file or URL access, remote exposure,
authentication, thumbnails, conversion, mutation, generation, review
persistence, approval, I02, dependencies, versioning, release, tag,
publication, Settings, `main`, force push, history rewriting, and branch
deletion are out of scope.

### Validation

- exact approved fifteen-file implementation allowlist, including the private
  production/Application read path, existing HTTP/Web composition, focused
  Python/Web tests, browser E2E, and this roadmap entry;
- focused Page-to-ledger-to-evidence-to-owner byte-correlation, fail-closed
  rejection, create-on-read manifest, exact-header, and no-disclosure tests;
- Ruff, mypy, full pytest, Web lint/typecheck/unit/build/E2E,
  security/audit/package, Markdown-link, and `git diff --check` gates;
- zero dependency, lockfile, persistence-schema, existing DTO, public-export,
  StateMachine, WorkflowEngine, Provider, I02, Settings, version, or `main`
  change;
- architecture, authority, security, LocalFile, workflow, approval, I02, and
  public-compatibility review;
- independent read-only review with P0 = 0 and P1 = 0; and
- required hosted CI, CodeQL, and post-merge verification.

### Authorization gate

V7-07 is complete. Its implementation authorization was exhausted by PR #33
and does not authorize a sixteenth file, live generation, Provider calls,
review persistence, approval, public-contract changes, StateMachine,
`WorkflowEngine`, persistence-schema or dependency changes, I02, `main`,
versioning, release, tag, publication, Settings, branch deletion, force push,
or history rewriting.

## V7-08 — Safe Local Human Visual Review and Approval Readiness

### Planning status

Design approved and frozen by
[RFC-V7-006: Safe Local Human Visual Review and Approval Readiness](RFC_V7_006_SAFE_LOCAL_HUMAN_VISUAL_REVIEW_READINESS.md).
The exact sixteen-file V7-08 implementation is complete and verified. PR #36
final head `df2b6fdae559de9c5ca7e0a59dfc12fa2fad28cd` was merged into `v7-dev`
at `ea45c7ef525198b2f77c236dced7742ee06857e1` after independent review and
all required local, hosted CI, CodeQL, merge, and post-merge gates passed.

### Objective

Define the smallest loopback-only, non-persistent bridge that lets a local
human submit an explicit visual checklist for the exact V7-07 Page image and
receive the advisory V7-06 readiness result without granting the browser
evidence-selection, quality, workflow, persistence, or approval authority.

### Inputs

- one existing Project and positive Page number from the local route;
- one bounded reviewer identity and timezone-aware review timestamp;
- exactly one closed outcome and rationale for every V7-06 human visual
  criterion; and
- one closed overall judgment and bounded rationale.

Attempt, asset, provenance, QA, Provider, digest, path, storage, root, URI,
URL, workflow, and approval identity are not caller inputs. The server derives
them, where applicable, from existing authoritative state.

### Outputs

- one transient, redacted `ready`, `needs_review`, or `blocked` assessment;
- deterministic ordered findings and missing-prerequisite codes;
- the persisted Page state used for assessment and `analysisOnly: true`; or
- a redacted fail-closed response with no reviewer text or internal evidence,
  storage, Provider, or approval metadata disclosure.

### Frozen behavior

- use one separately approvable additive loopback-only operation equivalent to
  `POST /projects/{project_id}/pages/{page_number}/visual-review-readiness`;
- reject query parameters and all caller-selected evidence, filesystem,
  Provider, workflow, and approval authority;
- resolve exactly Page → persisted generated artifact → applied workflow
  ledger proof → generation evidence and provenance → owner registry and safe
  PNG → canonical advisory Visual QA → server-bound transient judgment → the
  existing V7-06 readiness evaluator;
- independently revalidate that the Page still resolves to the exact safe
  V7-07 image before assessment;
- permit `Generated` only to produce `needs_review`, permit exact
  `QualityChecked` evidence to produce advisory `ready`, and never reopen an
  `Approved` Page;
- keep the submitted judgment and result transient, non-cacheable, visibly
  advisory, and absent after refresh, navigation, or replacement submission;
- keep the existing approval form independent: readiness does not fill,
  enable, disable, hide, replace, gate, or invoke approval, and reviewer
  identity never becomes `approvedBy`;
- open repository, ledger, evidence, registry, and asset state read-only and
  create, repair, migrate, checkpoint, or clean up nothing;
- perform no quality action, Page mutation, review persistence, readiness
  persistence, StateMachine transition, WorkflowEngine execution, Provider
  call, generation, retry, fallback, DNS, proxy, or outbound request;
- preserve current exact-origin CORS and expose no remote, LAN, wildcard,
  CLI, MCP, SDK, Plugin, or public Python surface; and
- remain completely independent of I02.

### Acceptance criteria

- the route and body together identify only one Project, Page, and complete
  bounded human judgment; every authoritative evidence identity is
  server-resolved;
- missing, duplicate, ambiguous, stale, corrupt, mismatched, unsafe, or
  incomplete authoritative state fails closed without fallback or repair;
- the exact V7-07 image and V7-06 readiness precedence remain authoritative;
- no request, refresh, repeat submission, error, or recovery path writes or
  repairs repository, sidecar, filesystem, browser, quality, review,
  readiness, workflow, or approval state;
- success and failure responses are redacted and non-cacheable, with no
  reviewer text, internal identifier, path, digest, Provider, redirect, or
  cache-validator disclosure;
- existing approval, Python, CLI, HTTP, Web, MCP, SDK, Plugin, Repository,
  LocalFile, Provider, generation, quality, V7-06, V7-07, v5/v6, and public
  compatibility is preserved;
- no existing DTO, public export, StateMachine, WorkflowEngine, schema,
  dependency, lockfile, package metadata, version, Settings, release, or
  `main` change is authorized; and
- the implementation stays within its exact sixteen-file allowlist and passes
  whitespace, architecture, compatibility, focused/full regression, Web,
  security, package, independent-review, CI, CodeQL, and post-merge gates with
  no P0 or P1 finding.

### Compatibility and exclusions

The approved implementation adds only the bounded loopback request/response,
private server-resolved evidence adapter, V7-07 private proof capability, and
transient Web form described by RFC-V7-006. Existing routes and DTOs, public
Python imports, CLI, MCP, SDK, Plugin, Repository and LocalFile formats,
Providers, StateMachine, WorkflowEngine, quality, Page states, and explicit
approval remain unchanged.

No migration is required. Durable review records, approval coupling,
authentication, arbitrary asset or URL selection, remote exposure, live
generation, Provider execution, I02, dependencies, versioning, release, tag,
publication, Settings, `main`, force push, history rewriting, and branch
deletion are out of scope.

### Validation

- exact approved sixteen-file implementation allowlist, including the V7-07
  private proof capability, V7-06 private server-resolved evidence adapter,
  Application/HTTP/Web delivery, focused tests, browser E2E, and this roadmap;
- focused and full Python regression, Ruff, mypy, Web lint/typecheck/unit/
  build/E2E, security/audit/package, Markdown-link, and `git diff --check`;
- zero dependency, lockfile, persistence-schema, existing DTO, public-export,
  StateMachine, WorkflowEngine, Provider, I02, version, Settings, or `main`
  diff;
- architecture, authority, privacy, approval-boundary, LocalFile-security,
  public-contract, and compatibility review;
- independent read-only review with P0 = 0 and P1 = 0; and
- required hosted CI, CodeQL, and post-merge verification.

### Authorization gate

V7-08 is complete. Its implementation authorization was exhausted by PR #36
and does not authorize a seventeenth file, review persistence, quality
execution, approval, Page mutation, Provider calls, live generation, existing
DTO or public-contract changes, StateMachine, WorkflowEngine, persistence
schema, dependencies, I02, `main`, versioning, release, tag, publication,
Settings, branch deletion, force push, or history rewriting.

## V7-09 — Safe Local Approved Asset Download

### Planning status

Design approved and frozen by
[RFC-V7-007: Safe Local Approved Asset Download](RFC_V7_007_SAFE_LOCAL_APPROVED_ASSET_DOWNLOAD.md).
Implementation is authorized only through the exact twelve-file V7-09
package. Completion requires its feature PR to pass all required local,
independent-review, hosted CI, CodeQL, merge, and post-merge gates.

The exact implementation allowlist is:

1. `src/manga_director/application/approved_asset_download.py`
2. `src/manga_director/api/composition.py`
3. `src/manga_director/api/workflow.py`
4. `tests/test_safe_local_approved_asset_download.py`
5. `web/lib/api/client.ts`
6. `web/lib/workflow-view.ts`
7. `web/components/page-workflow.tsx`
8. `web/tests/api-client.test.ts`
9. `web/tests/ui-contract.test.ts`
10. `web/e2e/mock-api.mjs`
11. `web/e2e/workflow.spec.ts`
12. `docs/ROADMAP_V7.md`

### Objective

Define the smallest loopback-only, read-only download boundary that returns
the exact V7-07 PNG for one existing Page only after the canonical workflow has
persisted that Page as `Approved` with explicit human approval evidence.

### Inputs

- one existing LocalFile Project ID from the route;
- one route-bounded positive Page number from the route;
- the Page's persisted `Approved` state, closed approval artifact, canonical
  terminal workflow history, and logical generated-asset descriptor; and
- the existing V7-07 ledger, generation evidence, owner registry, strict PNG,
  and exact-file lease proof.

Asset ID, attempt, Provider, digest, path, storage name, root, URL, format,
profile, filename, disposition, reviewer identity, and approval identity are
not caller inputs.

### Outputs

- one verified `image/png` attachment using a fixed Page-number filename; or
- one redacted fail-closed response with no approval, workflow, generation,
  storage, Provider, or filesystem disclosure.

The response is one local file download only. It is not print, Web, eBook,
package, archive, release-bundle, publication, or commercial-delivery
readiness.

### Frozen behavior

- use one separately approvable additive loopback-only operation equivalent to
  `GET /projects/{project_id}/pages/{page_number}/approved-asset-download`;
- before integer conversion or repository access, require the raw Page segment
  to match `^[1-9][0-9]{0,9}$` and be no greater than `2147483647`, without
  changing the existing Page model or public contract;
- reject query parameters, request bodies, transfer encoding, caller
  filenames, and all caller-selected asset, filesystem, Provider, export,
  workflow, and approval authority;
- reject requests containing `Range`, `If-Range`, `If-Match`,
  `If-None-Match`, `If-Modified-Since`, or `If-Unmodified-Since`;
- before repository or lease access, require exactly one parsed `Referer`
  origin in the existing local Web-origin allowlist together with
  `Sec-Fetch-Mode: navigate`, `Sec-Fetch-Dest: document`, and
  `Sec-Fetch-User: ?1`; reject absent, duplicate, malformed, or mismatched
  evidence, direct address-bar use, iframe navigation, preload, and non-browser
  callers without accepting `Origin`, a token, or a custom header instead;
- do not require `Sec-Fetch-Site`, because the allowed local Web origin and API
  may use different loopback host spellings; do not persist, log, or return the
  admission headers;
- require the authoritative Page to be exactly `Approved`, with the closed
  existing approval artifact and canonical final `QualityChecked` to
  `Approved` workflow-history entry;
- require the Page's one closed logical generated-asset descriptor and reuse
  the complete V7-07 private proof for the same Project and Page;
- return only bytes validated under the retained exact-file lease, with no
  path reopen after size, SHA-256, media-type, and strict-PNG validation;
- return `Content-Type: image/png`, `Content-Disposition` with the fixed
  `page-{page_number}.png` filename, `Cache-Control: no-store`, and
  `X-Content-Type-Options: nosniff`;
- emit no ETag, Last-Modified, Location, Content-Location, Accept-Ranges,
  redirect, Project title or ID, approver or reviewer identity, asset or
  attempt ID, Provider, digest, path, storage name, root, provenance, registry,
  ledger, or evidence metadata;
- keep the Web control explicit and user-initiated, derived only from Project
  ID and Page number; load, refresh, navigation, approval, or V7-08 assessment
  must not start a download;
- open only existing repository, ledger, evidence, registry, and asset state
  read-only and create, repair, migrate, checkpoint, copy, cache, or log
  nothing;
- fail closed on platforms that cannot retain the existing safe exact-file
  lease;
- perform no Page mutation, review or readiness persistence, quality action,
  approval, StateMachine transition, WorkflowEngine execution, Provider call,
  generation, retry, fallback, export-engine call, DNS, proxy, redirect, or
  outbound request;
- preserve current exact-origin CORS and expose no remote, LAN, wildcard, CLI,
  MCP, SDK, Plugin, or public Python surface;
- treat CORS as transport policy rather than download authority; the
  route-specific browser-initiated admission rule remains mandatory; and
- remain completely independent of I02.

### Acceptance criteria

- only an authoritative `Approved` Page with matching approval, terminal
  workflow history, logical artifact, V7-07 proof, and exact bytes succeeds;
- every earlier state and every missing, malformed, duplicate, ambiguous,
  stale, corrupt, mismatched, unsafe, oversize, digest-invalid, malformed-PNG,
  trailing-data, or partial-read state fails closed without fallback or repair;
- the server derives every authoritative identity and a fixed ASCII filename;
  the browser selects no asset, path, URL, filename, format, or export profile;
- the route admits only bounded Page-number input and explicit user-activated
  document navigation from an existing allowed local Web origin before any
  repository or lease access;
- success, failure, response abort, refresh, repeat request, and recovery write
  or repair no server/application-controlled repository, Page, sidecar,
  database, asset-root, service-filesystem, review, readiness, workflow,
  approval, export, or publication state;
- only a successful user-initiated response may cause the browser to create
  its chosen destination file or native download history; the feature neither
  selects nor programmatically reads, writes, records, or persists either;
- V7-08 remains transient and advisory and does not become a persisted or
  reconstructed prerequisite for download;
- existing generated-asset presentation, visual-review readiness, approval,
  Python, CLI, HTTP, Web, MCP, SDK, Plugin, Repository, LocalFile, Provider,
  generation, Project import/export, v5/v6, and public compatibility remain
  unchanged;
- no existing DTO, public export, StateMachine, WorkflowEngine, schema,
  dependency, lockfile, package metadata, version, Settings, release, or
  `main` change is authorized; and
- the implementation must stay within the approved exact twelve-file
  allowlist and pass focused/full regression, Web, security, package,
  independent-review, CI, CodeQL, and post-merge gates with P0/P1 = 0.

### Compatibility and exclusions

This implementation adds only the bounded binary GET, private Application
proof composition, and explicit Web download control described by
RFC-V7-007.

Existing routes and DTOs, public Python imports, CLI, MCP, SDK, Plugin,
Repository and LocalFile formats, Providers, StateMachine, WorkflowEngine,
quality, visual review, approval, Project import/export, and Page states remain
unchanged.

No migration is required. Batch/chapter/project download, caller filenames,
generic file serving, print/Web/eBook conversion, packaging, archives, release
bundles, publication, authentication, remote exposure, live generation,
Provider execution, I02, dependencies, versioning, release, tag,
Settings, `main`, force push, history rewriting, and branch deletion are out
of scope.

### Validation

- exact two-file docs allowlist: RFC-V7-007 and this roadmap entry;
- local Markdown-link resolution and `git diff --check`;
- zero source, test, dependency, lockfile, workflow, package-metadata, version,
  Settings, or `main` diff;
- architecture, approval-authority, exact-file security, privacy, export/
  publication boundary, public-contract, and compatibility review;
- independent read-only review with P0 = 0 and P1 = 0; and
- required hosted CI, CodeQL, and post-merge verification.

### Authorization gate

The V7-09 implementation authorization is limited to its exact twelve files
and the normal verified path through merge and post-merge checks. It does not
authorize a thirteenth file, general export, packaging, publication, review
persistence, quality execution, approval execution, Page mutation, Provider
calls, live generation, public-contract changes, StateMachine, WorkflowEngine,
persistence schema, dependencies, I02, `main`, versioning, release, tag,
Settings, branch deletion, force push, or history rewriting.

Any need for a current DTO or public API change, persistence, approval
coupling, remote surface, dependency, general export behavior, or I02
authority is a scope expansion and must stop.

## Epic 1 sequencing

| Issue | State | Dependency | Completion evidence |
| --- | --- | --- | --- |
| V7-01 Workflow HTTP Adapter | Complete | Accepted RFC-V7-001 and explicit v7 implementation authorization | PR #17 merged into `v7-dev` at `097a80d`; required CI passed; P0/P1 = 0; `main` unchanged |
| V7-02 Real Local Delivery End-to-End Gate | Complete | Completed V7-01 and explicit approval of the bounded V7-02 Planning Draft | PR #20 merged into `v7-dev`; final head `7d0034a2dad46c6ff982d03104d32d935d5db796`; merge commit `ad671b63a4135997ffc41e8ab95bb8a681668980`; required CI run #69 passed 10/10 jobs; independent review P0/P1/P2 = 0; exact seven-file allowlist; `main` unchanged |
| V7-03 Provider-Neutral Real Image Delivery | Complete and verified | Completed V7-02, accepted RFC-V7-002, and explicit approval of the exact ten-file implementation allowlist | PR #23 merged into `v7-dev` at `b688abb88bf07e7508a806c48f86c27b6e41fa5b`; CI run #82 passed 10/10 jobs; independent review P0/P1/P2 = 0; exact ten-file allowlist; feature branch retained; `main` unchanged |
| V7-04 ComfyUI Local Provider | Complete and verified | Completed V7-03, accepted RFC-V7-003, and explicit approval of the exact twelve-file implementation allowlist | PR #26 merged into `v7-dev` at `abd5a21a2597cb51286b666b23298b5f47450094`; post-merge CI run #95 passed 10/10 jobs; CodeQL run #19 passed 3/3 jobs; independent review P0/P1/P2 = 0; exact twelve-file allowlist; feature branch retained; `main` unchanged |
| V7-06 Human Visual QA and Approval Readiness | Complete and verified | Verified V7 generation and asset evidence on `v7-dev`, including PR #28, plus accepted RFC-V7-004 and the exact three-file implementation approval | PR #31 merged into `v7-dev` at `7c1d7d993e2c94dfd8c716ba7f6210c2b3117a42`; post-merge checks 13/13 and CodeQL 3/3 passed; independent review P0/P1/P2 = 0; exact three-file allowlist; feature branch retained; `main` unchanged |
| V7-07 Safe Local Generated Asset Presentation | Complete and verified | Completed V7-06, verified LocalFile generated-asset chain, accepted RFC-V7-005, and explicit approval of the exact fifteen-file implementation allowlist | PR #33 final head `d470dc4ddc5be9a33428fc39a9979262fc5578ba` merged into `v7-dev` at `9aad271fd8ff66d7516e2f066f55d2a0d62d4fbf`; post-merge checks 13/13 and CodeQL 3/3 passed after one approved Windows 3.11 rerun; independent review P0/P1/P2 = 0; exact fifteen-file allowlist; feature branch retained; `main` unchanged |
| V7-08 Safe Local Human Visual Review and Approval Readiness | Complete and verified | Completed V7-06 and V7-07, accepted RFC-V7-006, and explicit approval of the exact sixteen-file implementation package | PR #36 final head `df2b6fdae559de9c5ca7e0a59dfc12fa2fad28cd` merged into `v7-dev` at `ea45c7ef525198b2f77c236dced7742ee06857e1`; post-merge checks 13/13 and CodeQL 3/3 passed; independent review P0/P1/P2 = 0; exact sixteen-file allowlist; feature branch retained; `main` unchanged |
| V7-09 Safe Local Approved Asset Download | Implementation authorized; completion requires verified feature-PR merge | Completed V7-07 and V7-08, accepted RFC-V7-007, and explicit approval of the exact twelve-file implementation package | One additive loopback-only approved PNG download, private approval-plus-V7-07 proof composition, no mutation or export/publication coupling, P0/P1 = 0, and all required local/hosted/post-merge gates |

No later Epic 1 implementation is authorized solely by this roadmap.
Additional issues must be proposed with their own bounded scope, compatibility
analysis, validation plan, and approval state.

## Epic quality gates

Every Epic 1 change requires architecture-boundary, backward-compatibility,
workflow-invariant, LocalFile security, and delivery-contract review. P0 or P1
findings block merge. Documentation acceptance does not establish release
readiness, and release readiness does not authorize publication.
