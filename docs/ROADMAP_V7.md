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
The exact twelve-file V7-09 implementation is complete and verified. PR #39
final head `28f5cc0b10feb4d88f8d35d0c7ffd0b75d4fbc8f` was merged into `v7-dev`
at `547ab20bf2d92083bc800cf294087cf3ddf4efcb` after independent review and
all required local, hosted CI, CodeQL, merge, and post-merge gates passed.

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

V7-09 is complete. Its implementation authorization was exhausted by PR #39
and does not authorize a thirteenth file, general export, packaging,
publication, review persistence, quality execution, approval execution, Page
mutation, Provider calls, live generation, public-contract changes,
StateMachine, WorkflowEngine, persistence schema, dependencies, I02, `main`,
versioning, release, tag, Settings, branch deletion, force push, or history
rewriting.

## V7-10 — Durable Local Human Visual Review Evidence

### Planning status

Design approved and frozen by
[RFC-V7-008: Durable Local Human Visual Review Evidence](RFC_V7_008_DURABLE_LOCAL_HUMAN_VISUAL_REVIEW_EVIDENCE.md).
The exact fourteen-file V7-10 implementation is complete and verified. PR #42
final head `ac4d09c1fb9c5ab5dcaf4d96e475bd1044c3f048` was merged into `v7-dev`
at `3c83a067ece1a1b3d45f89d4816ffb47153f81d8` after independent review and
all required local, hosted CI, CodeQL, merge, and post-merge gates passed.

The approved design docs allowlist was:

1. `docs/RFC_V7_008_DURABLE_LOCAL_HUMAN_VISUAL_REVIEW_EVIDENCE.md`
2. `docs/ROADMAP_V7.md`

### Objective

Define the smallest local-only persistence boundary that records one explicit
V7-08 human visual judgment as immutable historical evidence for the exact
Page, generation attempt, output, provenance, Visual QA report, and safely
leased PNG resolved by the server.

### Inputs

- one existing LocalFile Project ID from the route;
- one route-bounded positive Page number from the route;
- the same bounded reviewer reference, timezone-aware review timestamp,
  complete criterion checklist, overall judgment, and rationale accepted by
  V7-08; and
- the server-resolved V7-07 proof and canonical V7-08 readiness report.

Review ID, attempt, asset, provenance, QA reference, Provider, digest, path,
storage name, root, URL, readiness result, prior assessment, approval identity,
and workflow command are not caller inputs.

### Outputs

- one immutable canonical review-evidence row newly appended or exactly
  confirmed as an idempotent replay;
- one redacted `ready`, `needs_review`, or human/QA-derived `blocked` result
  that explicitly reports successful evidence storage; or
- one fail-closed response with no partial row, repair, fallback, Page
  mutation, workflow action, or approval effect.

The record is historical evidence only. It is not approval, authentication,
authorization, a workflow transition, download eligibility, or publication
readiness.

### Frozen behavior

- keep the existing V7-08
  `POST /projects/{project_id}/pages/{page_number}/visual-review-readiness`
  transient and behaviorally unchanged;
- use one separately approvable additive loopback-only operation equivalent to
  `POST /projects/{project_id}/pages/{page_number}/visual-review-evidence`;
- require `application/json`, exactly one allowed local Web `Origin`, no query
  parameters, and the same closed human-input fields and validation as V7-08;
- reject caller-supplied Project/Page fields in the body and all review,
  attempt, asset, provenance, QA, Provider, digest, path, storage, URL,
  readiness, approval, and workflow authority;
- resolve the authoritative Page and reuse the complete V7-07 proof plus the
  canonical V7-08/V7-06 assessment path during the same request;
- add only a private V7-08 proof capability so transient assessment and
  durable recording share resolution and evaluation logic without changing
  existing `assess()` behavior;
- prohibit placeholder, unchecked, or `model_construct` reconstruction of a
  report or judgment;
- keep the exact-file lease active until the evidence transaction commits or
  rolls back and never reopen the asset by path after validation;
- make the private Application write service the sole owner of the retained
  proof: the sidecar owner closes only its transaction and connections, and
  the Application releases the proof exactly once after persistence finishes
  and before HTTP response construction;
- persist one closed canonical record containing the server-derived review
  identity, exact logical Page/generation/QA binding, complete human judgment,
  readiness result, payload digest, and binding fingerprint;
- store no image bytes, path, storage name, root, Provider metadata, approval,
  browser headers, current server timestamp, randomness, or secret;
- use one dedicated versioned private SQLite sidecar below the existing fixed
  Next Generation normal-execution durability root without changing Project,
  Page, Repository, LocalFile, ledger, generation-evidence, registry, approval,
  or workflow schemas;
- create the sidecar only on an explicit valid record operation when it is
  absent and no conflicting state exists;
- treat an exact canonical retry as idempotently confirmed, append every
  distinct valid review, and never update, delete, overwrite, merge, compact,
  migrate, repair, or select a latest/best review;
- allow only a private exact-ID lookup for idempotency, verification, and
  tests; add no HTTP listing, search, read, delete, update, export, or recovery
  surface;
- fail closed on invalid input, earlier or `Approved` Page state, missing or
  inconsistent proof, unsupported exact-file lease, unsafe filesystem
  identity, sidecar conflict, corruption, schema mismatch, transaction, or I/O
  failure without recording infrastructure failure as a review judgment;
- allow `Generated` to persist only `needs_review` or human/QA-derived
  `blocked`; allow `QualityChecked` to persist `ready`, `needs_review`, or
  human/QA-derived `blocked`; never reopen `Approved`;
- keep `analysisOnly: true` for readiness and return only redacted status,
  boolean, Page state, findings, missing-prerequisite codes, storage success,
  and idempotent-replay status;
- add a separate explicit Web control; Page load, image load, refresh,
  navigation, transient assessment, quality, approval, or download must never
  record evidence;
- do not copy reviewer identity into approval or use a record to enable, fill,
  gate, invoke, replace, revoke, or deny approval;
- keep V7-09 completely independent of the new evidence sidecar;
- preserve existing loopback binding and exact-origin CORS without DNS, proxy,
  redirect, remote request, Provider call, retry, fallback, or I02; and
- expose no CLI, MCP, SDK, Plugin, public Python, LAN, wildcard, cloud, or
  remote surface.

### Persistence boundary

The implemented private owner is equivalent to:

`_next_generation_normal_execution/review-evidence/human-visual-review-evidence.sqlite3`

It is a new isolated private version-1 sidecar, not a Project or Repository
migration. The first valid explicit write may create its fixed directory and
schema. Existing invalid, unsafe, corrupt, or unsupported state is never
repaired or migrated. Any standalone reader opens only an existing database
with `mode=ro` and query-only semantics.

### Approval and workflow boundary

`ready` remains advisory. V7-10 adds no Page state, transition, command,
event, rejection, revocation, approval prerequisite, approver selection, or
review-selection policy. The existing explicit approval action remains the
sole authority for `QualityChecked` to `Approved`, and V7-09 continues to rely
only on its existing authoritative approval proof.

Any future approval-to-review evidence linkage requires a separate RFC and
explicit authorization.

### Implementation allowlist

The implementation was completed within the approved exact fourteen files:

1. `src/manga_director/production/next_generation_durable_human_visual_review_evidence.py` (new)
2. `src/manga_director/application/human_visual_review_evidence.py` (new)
3. `src/manga_director/application/human_visual_review_readiness.py`
4. `src/manga_director/api/composition.py`
5. `src/manga_director/api/workflow.py`
6. `tests/test_next_generation_durable_human_visual_review_evidence.py` (new)
7. `tests/test_safe_local_human_visual_review_evidence.py` (new)
8. `web/lib/api/types.ts`
9. `web/lib/api/client.ts`
10. `web/components/human-visual-review-form.tsx`
11. `web/tests/api-client.test.ts`
12. `web/tests/ui-contract.test.ts`
13. `web/e2e/mock-api.mjs`
14. `web/e2e/workflow.spec.ts`

The existing Page view and V7-08 visibility predicate are sufficient, so
`web/components/page-workflow.tsx` and `web/lib/workflow-view.ts` are excluded.
LocalFile, Project, StateMachine, WorkflowEngine, approval, V7-09, package
exports, dependency, and lock files are also excluded.

### Acceptance criteria

- one explicit valid request records or idempotently confirms exactly one
  canonical immutable human visual review evidence row;
- Page, attempt, output, provenance, QA, readiness, and review identities are
  server-resolved or server-derived and match the same safely leased bytes;
- exact-file lease retention covers the final database commit or rollback;
- the Application writer alone releases the retained proof exactly once after
  persistence completes and before an HTTP response can be aborted;
- exact retry is idempotent, a distinct valid judgment appends, and no record
  is updated, deleted, overwritten, selected as latest, or used as approval;
- `ready`, `needs_review`, and human/QA-derived `blocked` may be historical
  evidence, while invalid input, unavailable proof, corruption, or
  infrastructure failure never becomes a review row;
- the existing V7-08 endpoint remains transient and creates no sidecar;
- Page load, image load, refresh, quality, approval, and V7-09 download create
  no review evidence;
- Project, Page, `review`, `approval`, workflow history, StateMachine,
  WorkflowEngine, existing schemas, routes, DTOs, public Python API, CLI, MCP,
  SDK, Plugin, Provider, dependencies, I02, v5, and v6 remain unchanged;
- errors and responses expose no human text, internal identity, Provider,
  digest, SQL, path, storage, root, redirect, or cache validator;
- the implementation stayed within its approved exact fourteen-file allowlist
  and passed focused/full regression, Web, security, package,
  independent-review, CI, CodeQL, and post-merge gates with P0/P1 = 0; and
- this design diff stays within the exact two-file docs allowlist.

### Validation

- exact two-file docs allowlist: RFC-V7-008 and this roadmap entry;
- local Markdown-link resolution and `git diff --check`;
- zero source, test, dependency, lockfile, workflow, package-metadata, version,
  Settings, or `main` diff;
- architecture, persistence-owner, exact-file lease, privacy,
  approval-authority, public-contract, and compatibility review;
- independent read-only review with P0 = 0 and P1 = 0; and
- required hosted CI, CodeQL, and post-merge verification.

### STOP conditions

A second completion-state file, a fifteenth implementation file, existing DTO
or public export change, Project/Repository/LocalFile or existing sidecar
schema change,
`Page.review` or approval coupling, StateMachine, WorkflowEngine, V7-09
eligibility, dependency, Provider, I02, remote surface, exact-lease weakening,
sidecar repair/migration, unresolved P0/P1, failed required check, conflict, or
scope drift requires a new explicit decision.

### Authorization gate

V7-10 is complete. Its exact fourteen-file implementation authorization was
exhausted by PR #42 and does not authorize a fifteenth file, an additional
route or Web change, sidecar or schema change, runtime persistence behavior,
Page or workflow mutation, quality, approval, Provider, generation, I02,
dependencies, `main`, versioning, release, tag, Settings, branch deletion,
force push, or history rewriting.

## V7-11 — Safe Local Human Visual Review Evidence History

### Planning status

Design approved and frozen by
[RFC-V7-009: Safe Local Human Visual Review Evidence History](RFC_V7_009_SAFE_LOCAL_HUMAN_VISUAL_REVIEW_EVIDENCE_HISTORY.md).
The exact fifteen-file V7-11 implementation is complete and verified. PR #45
final head `32a0386dce4101606fd1c66e748eef3ffa213e62` was merged into `v7-dev`
at `7ef060d98b631ed2b9492ee9c3e0b0560c70b08e`. PR checks passed 24/24;
post-merge CI run #156 passed 10/10 jobs and CodeQL run #59 passed 3/3 jobs;
independent read-only review reported P0/P1/P2 = 0/0/0.

The approved design docs allowlist was:

1. `docs/RFC_V7_009_SAFE_LOCAL_HUMAN_VISUAL_REVIEW_EVIDENCE_HISTORY.md`
2. `docs/ROADMAP_V7.md`

### Objective

Define the smallest loopback-only, read-only boundary that lets a local human
explicitly inspect the immutable V7-10 review-evidence history for one
authoritative Page without changing the store, selecting a preferred review,
or affecting approval, workflow, generation, or download.

### Inputs

- one existing LocalFile Project ID from the route;
- one route-bounded positive Page number from the route;
- the authoritative LocalFile Page identity and current state; and
- the existing V7-10 private version-1 review-evidence sidecar, when present.

Review ID, output, attempt, provenance, QA reference, reviewer, timestamp,
status, digest, path, Provider, approval, sort, filter, limit, cursor, and
workflow command are not caller inputs.

### Outputs

- one complete bounded Page history containing zero or more immutable V7-10
  records in canonical `review_id` order; or
- one redacted fail-closed response with no partial history, write, repair,
  fallback, Page mutation, workflow action, approval effect, or download
  eligibility effect.

Every returned `ready`, `needs_review`, or `blocked` result is historical
advisory evidence only. It is not approval, authentication, authorization, a
workflow transition, V7-09 eligibility, or publication readiness.

### Frozen behavior

- reuse the implemented V7-10 sidecar, schema version 1, canonical payload,
  digest, binding, and filesystem validation without changing them;
- use one separately approvable additive loopback-only operation equivalent to
  `GET /projects/{project_id}/pages/{page_number}/visual-review-evidence` while
  leaving the existing V7-10 POST on the same resource unchanged;
- accept no request body or query parameters and no caller-selected review,
  output, attempt, provenance, QA, Provider, storage, path, status, sort,
  filter, cursor, limit, approval, or workflow authority;
- require the same bounded raw positive Page-number form plus exact local
  `Origin`, allowed local `Referer`, `Sec-Fetch-Mode: cors`,
  `Sec-Fetch-Dest: empty`, and explicit JSON `Accept` before Project or
  sidecar access;
- reject transfer encoding, non-zero content length, range requests,
  conditional requests, missing or duplicate admission headers, malformed
  origin evidence, and remote or LAN callers;
- load the authoritative Page and bind records by exact Project ID, Page ID,
  and Page number;
- allow current `Generated`, `QualityChecked`, and `Approved` Pages without
  reopening review or approval;
- treat a completely absent review-evidence directory and database as an
  empty complete history while treating a present directory with a missing
  database as conflicting unavailable state;
- open an existing sidecar only with `mode=ro`, `timeout=0.0`, and verified
  query-only semantics after safe identity and rollback-journal preflight;
- enforce one server-owned bounded SQLite read-work budget across schema
  validation, complete row validation, and the Page query, with whole-request
  failure rather than skipped or partial records when the budget is exhausted;
- validate the exact V7-10 schema and every stored row before returning any
  record;
- return matching records only in ascending `review_id` order as a stable
  technical order with no recency, chronology, quality, approval, or
  supersession meaning;
- return at most 32 records and at most 1,048,576 UTF-8 JSON bytes, failing the
  complete request rather than truncating, paginating, ranking, or selecting a
  subset;
- include only the review ID, output asset ID, reviewer reference, reviewed-at
  value, recorded Page state, complete checklist, overall judgment and
  rationale, advisory status, matching `ready`, findings, missing prerequisites,
  and `analysisOnly: true` for each record;
- exclude Project ID, Page ID, attempt, provenance, QA reference, fingerprint,
  digest, Provider, image bytes, path, storage, root, database, SQL, browser
  headers, approval identity, workflow command, next state, and download
  eligibility from the response;
- add one explicit Web history control that performs no request on Page load,
  image load, refresh, navigation, polling, assessment, evidence recording,
  quality, approval, or download;
- render reviewer-authored text only as text and retain history only in current
  browser memory without local storage, IndexedDB, cookies, service-worker
  cache, or background queues;
- label every result, including `ready`, as historical advisory evidence and
  never fill, enable, gate, invoke, replace, revoke, or deny approval;
- never copy `reviewerId` into `approvedBy`;
- never update, delete, replace, repair, compact, vacuum, checkpoint, migrate,
  normalize, or clean up the sidecar;
- keep V7-09 completely independent of review-evidence history;
- perform no StateMachine transition, WorkflowEngine execution, Provider call,
  generation, retry, fallback, DNS, proxy, redirect, outbound request, or I02;
  and
- expose no CLI, MCP, SDK, Plugin, public Python, LAN, wildcard, cloud, or
  remote surface.

### Public contract, security, and privacy

The implementation is one additive closed JSON GET and one explicit Web-only
history panel. Success and failure use `Cache-Control: no-store` and
`X-Content-Type-Options: nosniff` and emit no ETag, Last-Modified, Location,
Content-Location, redirect, filename, or cache validator.

The response intentionally contains bounded reviewer-authored evidence, so it
is fetched only after explicit local human action. Reviewer text never becomes
HTML, Markdown, a URL, path, header, log format, SQL fragment, credential,
approval identity, or authorization input. Errors reveal no human text,
internal identity, Provider, digest, path, storage, root, database, SQL,
traceback, row count, or filesystem detail.

No access log, analytics, telemetry, notification, authentication, role,
identity-verification, secret, or browser persistence feature is added.

### Compatibility and exclusions

The V7-10 POST route, request, response, append, idempotency, immutable row,
payload, schema, journal, and exact-ID lookup behavior remain unchanged.
Existing HTTP DTOs and public Python imports remain unchanged; new contracts
are additive, closed, and private outside the local HTTP/Web surface.

Project, Page, Repository, LocalFile, workflow history, review, approval,
ledger, generation evidence, registry, asset, StateMachine, WorkflowEngine,
Provider, generation, quality, V7-08, V7-09, v5, and v6 behavior remain
unchanged. No migration, index, dependency, lockfile, package metadata,
version, release, tag, Settings, `main`, or I02 change is permitted.

### Implementation allowlist

The implementation was completed within the approved exact fifteen files:

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

LocalFileRepository, Project and Page models, package exports, StateMachine,
WorkflowEngine, approval, V7-09, Provider, generation, dependency, and lock
files are excluded. A sixteenth implementation file is a scope expansion.

### Acceptance criteria

- one explicit local GET returns only immutable V7-10 records for one exact
  authoritative Page;
- a completely absent store returns an empty complete history and creates
  nothing;
- an existing store is opened only read-only/query-only and every row is
  validated before any result is returned;
- Project ID, Page ID, and Page number bind every returned record;
- all matching records are returned within the fixed complete-history bounds
  without truncation, latest/best selection, or approval meaning;
- one unsafe, corrupt, unsupported, duplicate, ambiguous, busy, or oversized
  condition prevents partial success and causes no repair;
- `Approved` Pages retain read-only history access without reopening review or
  changing approval;
- Page load, refresh, V7-08 assessment, V7-10 record, quality, approval, and
  V7-09 download never fetch or change history automatically;
- reviewer evidence is exposed only by an explicit non-cacheable local read
  and is not stored by the browser or reused as authority;
- `ready` cannot affect approval, Page state, StateMachine, WorkflowEngine, or
  V7-09 eligibility;
- existing schemas, routes, DTOs, public Python API, CLI, MCP, SDK, Plugin,
  Repository, LocalFile, Provider, dependencies, I02, v5, and v6 remain
  unchanged; and
- the implementation stayed within its approved exact fifteen-file allowlist
  and passed focused/full regression, Web, security, package, CI, CodeQL, and
  post-merge gates with no blocking failure; and
- this completion-state diff stays within the exact two-file docs allowlist.

### Validation

- exact two-file docs allowlist: RFC-V7-009 and this roadmap entry;
- local Markdown-link resolution and `git diff --check`;
- zero source, test, dependency, lockfile, workflow, package-metadata, version,
  Settings, or `main` diff;
- architecture, store ownership, read-only SQLite, privacy, approval
  separation, public-contract, and compatibility review;
- independent read-only review with P0 = 0 and P1 = 0; and
- required hosted CI, CodeQL, and post-merge verification.

The completed implementation passed focused absent, empty, one-record,
multiple-record, restart, ordering, binding, state, bound, admission,
redaction, corruption, unsafe-file, WAL, schema, duplicate, lock,
bounded-read-work, I/O, no-partial-result, no-mutation, Web-explicit-action,
approval-separation, V7-09-independence, no-Provider, no-generation, and no-I02
tests together with the full Python, Web, browser, security, audit, package,
compatibility, exact-allowlist, and whitespace gates.

### STOP conditions

A third docs file, a sixteenth implementation file, V7-10 schema or row
change, update/delete/repair/compact/vacuum/checkpoint/migration, partial
history, latest/best selection, approval linkage, existing DTO or public
export change, Project/Repository/LocalFile schema change, StateMachine,
WorkflowEngine, V7-09 eligibility, Provider, generation, I02, dependency,
lockfile, CORS, remote surface, unresolved P0/P1, failed required check,
conflict, or scope drift requires a new explicit decision.

### Authorization gate

V7-11 is complete. Its exact fifteen-file implementation authorization was
exhausted by PR #45 and does not authorize a sixteenth file, another route or
Web change, sidecar or schema change, runtime mutation, approval linkage, Page
or workflow mutation, quality, V7-09 changes, Provider, generation, I02,
dependencies, `main`, versioning, release, tag, publication, Settings, branch
deletion, force push, or history rewriting.

## V7-12 — Durable Local Human Visual Review Evidence-Linked Approval

### Planning status

Docs-only design approved and frozen by
[RFC-V7-010: Durable Local Human Visual Review Evidence-Linked Approval](RFC_V7_010_DURABLE_LOCAL_HUMAN_VISUAL_REVIEW_EVIDENCE_LINKED_APPROVAL.md).
The exact twenty-one-file V7-12 implementation is complete and verified. PR
#48 final head `5835de2c5d890a40a232f1ff7ad9a7a690240eff` was merged into
`v7-dev` at `a02eedf38cd79c43c2add68ac08c332dab5eefb8`. PR CI run #166 passed
10/10 jobs and PR CodeQL run #65 passed 3/3 jobs; post-merge CI run #167
passed 10/10 jobs and CodeQL run #66 passed 3/3 jobs; independent read-only
review reported P0/P1/P2 = 0/0/0.

The approved design docs allowlist was exactly:

1. `docs/RFC_V7_010_DURABLE_LOCAL_HUMAN_VISUAL_REVIEW_EVIDENCE_LINKED_APPROVAL.md`
2. `docs/ROADMAP_V7.md`

### Objective

Define the smallest loopback-only operation that lets a local human explicitly
approve one authoritative `QualityChecked` Page while durably naming one exact
immutable V7-10 review evidence record. Inside the existing durable LocalFile
Page fence and after loading the fresh revision, the operation must re-prove
the record against the current exact generated asset before delegating the
unchanged transition to the existing workflow owners.

V7-12 is additive and optional. Existing ordinary approval remains available
and unchanged. Historical evidence, a `ready` result, history display, or record
selection never approves a Page without a separate explicit submit and an
independent `approvedBy` value.

### Inputs

- one existing LocalFile Project ID and one bounded positive Page number from
  the route;
- one caller-selected exact `reviewId`; and
- one independently entered non-empty `approvedBy` reference.

The operation accepts no generic metadata, output, attempt, provenance, QA,
Provider, path, storage, digest, status, sort, fallback, or workflow command.
`reviewerId` is never copied into, suggested as, or compared with `approvedBy`.

### Outputs

- the existing Page-detail response after one normal durable
  `QualityChecked -> Approved` transition; and
- an approval artifact containing exactly `approved_by` plus the selected
  `review_evidence_id` for this new operation; or
- one redacted fail-closed response with no evidence mutation, direct Page
  save, alternate approval, automatic retry, or fallback record.

Legacy ordinary approval continues to contain only `approved_by`.

### Frozen behavior

- add one separately approvable closed local POST equivalent to
  `/projects/{project_id}/pages/{page_number}/evidence-linked-approval`;
- require exact local browser-write admission, canonical path values, closed
  JSON, explicit JSON content negotiation, and no query parameters before
  Project or evidence access;
- require the caller to select one exact `reviewId`; never enumerate or choose
  a latest, newest, best, winning, consensus, only, first, or last record;
- read the record only through the V7-10 owner using the existing read-only,
  query-only, bounded, schema-validating, fail-closed exact-ID path;
- require exact Project ID, Page ID, Page number, and authoritative current
  `QualityChecked` state binding;
- require the stored record itself to have `pageState: QualityChecked`,
  `status: ready`, `ready: true`, no findings, and no missing prerequisites;
- acquire the existing durable LocalFile Page fence, load the fresh revision,
  and only then invoke the private Application validation gate;
- reconstruct the complete stored human submission inside that fence and use
  the existing V7-08 service to re-prove readiness against the same current
  Page, exact safe generated asset, generation attempt, provenance, and Visual
  QA binding;
- require the Page identity, state, approval absence, image, quality, and
  workflow history used by re-proof to equal the freshly fenced context;
- require the recomputed V7-10 canonical payload to equal the immutable stored
  payload exactly, with no tolerance, normalization, partial comparison, or
  substitution;
- retain both the Page fence and existing exact-file lease through transition,
  conditional commit, post-commit verification, event publication, failure,
  and cleanup, releasing the proof lease before the fence exactly once;
- preserve existing durable failure semantics: pre-commit failure leaves the
  Page unchanged, while a later verification or event-publication failure may
  leave it durably Approved and requires authoritative reload without
  compensation, retry, or a false rollback claim;
- reserve the evidence-link input to the new private Application service so
  generic approval metadata cannot forge it;
- run approval only through the existing durable LocalFile command path,
  approval agent, WorkflowEngine, and StateMachine;
- leave the StateMachine and WorkflowEngine source and behavior unchanged;
- keep ordinary approval available and unchanged for legacy callers and Pages;
- persist only the explicit approver and exact evidence reference, copying no
  evidence payload, reviewer text, status, timestamp, digest, path, or policy;
- allow V7-09 to validate both closed approval artifact shapes while keeping
  its existing eligibility rules identical and never reading review evidence;
- expose one deliberate linked-approval action only for an explicitly displayed
  eligible history record on a `QualityChecked` Page;
- require the human to enter `approvedBy` separately and submit once; viewing,
  loading, or selecting evidence performs no transition;
- keep the ordinary approval form visible as an unlinked compatibility path;
- perform no background fetch, auto-submit, polling, optimistic approval,
  retry, queue, browser persistence, or auto-refresh except the existing
  post-success server refresh; and
- add no Provider, generation, CLI, MCP, SDK, Plugin, public Python, LAN,
  wildcard, cloud, remote, or I02 surface.

### Compatibility and exclusions

The V7-08 readiness calculation, V7-10 schema and immutable rows, V7-10 record
POST, V7-11 history GET, existing approval request and response, StateMachine
transitions, WorkflowEngine sequencing, Repository protocols, and LocalFile
Project/Page model schemas remain unchanged.

The evidence-linked artifact is an additive closed shape within the existing
`Page.approval` mapping. Existing persisted Pages remain valid and are not
migrated. V7-09 may recognize the optional reference but cannot make evidence a
new eligibility rule or dereference it during download.

No dependency, lockfile, package metadata, version, release, tag, publication,
Settings, `main`, I02, branch-deletion, force-push, or history-rewrite change is
permitted.

### Implementation allowlist

The implementation was completed within the approved exact twenty-one files:

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

The V7-10 store and writer, V7-08 readiness service, V7-11 history service,
Page/Project models, repositories, StateMachine, WorkflowEngine, dependencies,
lockfiles, Provider, generation, CLI, MCP, SDK, Plugin, and I02 are excluded. A
twenty-second implementation file was not required. Any future twenty-second
implementation file is a scope expansion.

### Acceptance criteria

- one explicit local submit supplies one exact review ID and one separate
  explicit approver reference;
- no history order, timestamp, status, record count, or UI state selects a
  record automatically;
- stored evidence is exact, immutable, `QualityChecked`, `ready`, and bound to
  the authoritative Page;
- current readiness is re-proved only against the freshly loaded revision
  inside the same Page fence and reproduces the stored canonical payload while
  the exact asset lease remains held;
- generic approval cannot forge a link and ordinary approval remains unchanged;
- the existing StateMachine and WorkflowEngine perform the only transition and
  are not modified;
- evidence-linked approval survives restart with only the exact reference added
  to its existing approval artifact;
- V7-09 accepts legacy and linked artifacts under identical eligibility rules;
- V7-10/V7-11 evidence remains unchanged on success and failure;
- Project/Page model schemas, repositories, public APIs, Provider, generation,
  dependencies, I02, v5, and v6 remain unchanged; and
- the implementation stayed within its approved exact twenty-one-file
  allowlist and passed focused/full regression, Web, security, package, CI,
  CodeQL, and post-merge gates with no blocking failure; and
- this completion-state diff stays within the exact two-file docs allowlist
  and independent review reports no P0/P1 issue.

### Validation

- exact two-file docs allowlist and zero non-doc diff;
- Markdown-link resolution and `git diff --check`;
- architecture, approval authority, durable execution, lease lifetime,
  LocalFile security, privacy, V7-09 compatibility, public-contract, and V6 LTS
  review; and
- independent read-only review with P0 = 0 and P1 = 0.

The completed implementation passed focused stored/current binding,
ready/non-ready, fresh-revision in-fence validation, pre-fence and concurrent
change rejection, anti-forgery, lease/fence release ordering, rollback,
persistence, post-commit verification/event failure and authoritative reload,
restart, ordinary approval compatibility, V7-09 parity, Web explicit-action,
redaction, and no-evidence-mutation tests together with the full Python, Ruff,
Windows/Linux mypy, Web, browser-E2E, security/audit, package, compatibility,
exact-allowlist, CI, and CodeQL gates defined by RFC-V7-010.

### STOP conditions

A third docs file, a twenty-second implementation file, automatic record
selection, inferred approval, reviewer-to-approver copy, V7-10 mutation or
schema change, Page/Project/Repository/LocalFile model schema change,
StateMachine or WorkflowEngine change/bypass, evidence-dependent V7-09
eligibility, Provider, generation, remote access, I02, dependency, lockfile,
package, version, release, tag, publication, Settings, `main`, branch deletion,
force push, history rewrite, unresolved P0/P1, failed required check, conflict,
or scope drift requires a new explicit decision.

### Authorization gate

V7-12 is complete. Its exact twenty-one-file implementation authorization was
exhausted by PR #48 and does not authorize a twenty-second file, another route
or Web change, evidence-store or schema change, another approval behavior,
V7-09 eligibility change, StateMachine or WorkflowEngine change, Provider,
generation, I02, dependencies, `main`, versioning, release, tag, publication,
Settings, branch deletion, force push, or history rewriting.

## V7-13 — Private Panel-Aware Page Generation Foundation

### Planning status

The RFC-V7-011 Slice 1 through Slice 4 implementation and validation closure
are complete and verified. PR #54 merged Slice 4 into
`validation/rfc-v7-011-slice-3` at
`4719c55a3ade5b3f10f75d4432f07bcbc958d6a0`. PR #55 then merged the completed
validation branch into `v7-dev` at
`a760488f43f84e28978fe5b3bf1d25e44b9b8396`; PR #55 CI passed, post-merge CI
run `40273044192` passed all 10 jobs, and final independent closure reported
P0/P1/P2 = 0/0/0.

### Objective

Provide a private, durable foundation for one-Page panel-aware generation that
keeps panel planning, provider attempts, generated assets, generation evidence,
deterministic composition, output proof, and restart behavior bound to the same
authoritative LocalFile Page execution while preserving the existing legacy
single-canvas path and exactly-one-Page workflow invariant.

### Completion boundary

The completed implementation includes the private Slice 1 through Slice 4
kernel, durable persistence, panel-aware orchestration, and safe generation-mode
admission. It does not add a public HTTP or Web route, CLI, MCP, SDK, Plugin, or
public Python activation surface. Public routing remains disabled.

Release or public activation, live Provider or ComfyUI validation, and I02 were
not performed. Those remain separate future work and require their own bounded
scope, validation plan, and explicit authorization.

### Authorization gate

RFC-V7-011 implementation and validation are complete. This completion record
does not authorize public routing, release, publication, live Provider or
ComfyUI execution, I02, another implementation slice, dependency or lockfile
changes, public API changes, branch deletion, force push, or history rewriting.

## V7-14 — Safe Panel-Aware Activation Bridge

### Completion status

Complete and verified; public routing disabled. The completed design and
implementation are recorded in
[RFC-V7-012: Safe Panel-Aware Activation Bridge](RFC_V7_012_SAFE_PANEL_AWARE_ACTIVATION_BRIDGE.md).
The private deterministic bridge converts persisted Storyboard and
PromptBuilt artifacts to the V7-13 private `PageGenerationPlan`, plus a private
adapter from the V7-13 `PanelProviderExecutionPort` to the existing V7-04
`ComfyUIImagePrivateTransport`.

The design preserves V7-13 mode exclusion, durable admission and provider-start
ordering, at-most-once execution, fail-closed restart recovery, exact evidence
binding, and disabled public routing. The known Storyboard default action
`advance the page purpose` is invalid under the concrete prompt contract, and
the default character identity `protagonist` is also rejected. Current
Storyboard artifacts do not supply panel rectangles. The bridge must require
an already-present explicit concrete action and exact supported layout input;
it must not infer or auto-fill either. These are prominent stop conditions,
alongside missing required plan values `narrative_intent`,
`continuity_bindings`, and `constraints`. Storyboard also has no explicit
`panel_id`, which the bridge derives deterministically from the content binding
and panel order; it is not a required explicit source field. `Page.storyboard`
and `Page.prompt` are plain dict artifacts without stable reference fields, so
the bridge derives safe source references from their full canonical content
digests. The exact revision and page fingerprint enter the `source_binding_v1`
digest that determines `plan_id`; the V7-13 mode claim binds revision and page
fingerprint directly, and the operation binds revision directly. These are not
new `PageGenerationPlan` fields. RFC-V7-012 fixes one unambiguous seven-field
transport `raw_prompt` preimage, a distinct full `panel_prompt`, and literal
canonical full-digest derivations for every generated request, attempt,
panel-output/evidence, composition attempt (the frozen operation identity),
composition provenance/evidence, composite asset, and application ID; see it for
the full closed mapping and fail-closed rules. Missing or invalid required
input blocks conversion. The ComfyUI sequence is read-only
preflight/prepare after reservation, authority recheck and durable
provider-start, then one prepared submit, as implemented and tested in Slices
2–3.

HTTP/Web/Application public activation remains V7-15+; I02, live ComfyUI,
release/publication, `main`, dependencies/lockfiles, schema/migration, and
public API remain unperformed and unapproved.

### Authorization gate

| Slice | Pull request | PR head | Merge commit | PR-head CI |
| --- | --- | --- | --- | --- |
| 1 — deterministic converter | [#61](https://github.com/esuforesuto-cmd/manga-director-oss/pull/61) | `cd125b550b55ff016a737a8e2e022c02196e6f9c` | `c9b0c27ef1df8104f70b573c9dd7c10266b523df` | 24/24 succeeded |
| 2 — private ComfyUI adapter | [#62](https://github.com/esuforesuto-cmd/manga-director-oss/pull/62) | `133d3c17860817a37e5fe66b489b46469104b3c9` | `4feeae65cab5a48397f274164422588d4e2f7adc` | 24/24 succeeded |
| 3 — operation composition | [#63](https://github.com/esuforesuto-cmd/manga-director-oss/pull/63) | `383c94ec3c14f67b48aed4ac484dfd81d6326d26` | `1daff9e58bd52058e44175c99b4248ea321a30f5` | 24/24 succeeded |

Final independent review of the completed Slice 3 diff: P0 = 0, P1 = 0,
P2 = 0. CI counts are PR-head
results; no post-merge CI result is claimed. The final implementation changed
the seven unique files listed in RFC-V7-012. All three feature branches remain
present; none was deleted. This completion record does not authorize follow-up
implementation or expand the scope above.

## V7-15 — Safe Local Panel-Aware Generation Activation

### Slice status

Slice 1 — private Local/Application activation — is Complete and verified.
Slice 2 — dedicated HTTP route — is merged in PR #68; post-merge CI passed
10/10 and CodeQL passed 3/3. Slice 3 — explicit Web activation — is being
implemented in an isolated branch under the separately approved exact
17-file allowlist. Local verification and independent review are pending.
The design and staged plan are in
[RFC-V7-013: Safe Local Panel-Aware Generation Activation](RFC_V7_013_SAFE_LOCAL_PANEL_AWARE_GENERATION_ACTIVATION.md).
V7-15 Slice 2 enables the dedicated route only in the concrete LocalFile HTTP
composition. Remote deployment remains disabled, and the existing lack of
authentication is unchanged; CORS and same-origin request checks are not
authentication. Slice 3 does not add authentication and remains local-only.

The implementation preserves the existing generic `/generate` behavior and
adds a separate panel-aware HTTP route; an explicit Web “Generate panels”
action is the separate Slice 3 Web control.
The browser may provide only bounded `authorizedBy` attribution, a V7-04
validated `checkpointName`, and explicit ordered rectangles for the supported
layout profile. It cannot provide authorization/attempt IDs, provider endpoint,
graph, prompt, or transport configuration. Layout is never inferred. The
private application path must compose the completed V7-14 operation and V7-13
authorities with real V7-04 validation, then apply the generated result through
the existing StateMachine/EventBus/CAS/application boundary. Before the Page
transition, identical retries at the same revision resolve to the same
references, mode claim, and operation. After the Page is `Generated`, a retry
returns only a bounded read-only `already_generated` result when existing
durable authorities verify the exact original activation and completed output
binding; otherwise it fails closed with `revision_conflict`. Both outcomes
make zero provider calls and no writes. Changed inputs, ambiguous authority
state, or unsupported inputs fail closed without a new executable attempt.

Sequence: Slice 1 private Local/Application activation and safe Page
application is complete; Slice 2 is merged; Slice 3 Web implementation and
local validation are in progress within its approved 17-file allowlist. This
record authorizes no changes outside that scope and does not change frozen
contracts. Live
ComfyUI, I02, `main`, release/publication, dependency/lockfile changes,
schema/migration, and branch deletion remain unperformed and unapproved; no
further branch operations are authorized.

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
| V7-09 Safe Local Approved Asset Download | Complete and verified | Completed V7-07 and V7-08, accepted RFC-V7-007, and explicit approval of the exact twelve-file implementation package | PR #39 final head `28f5cc0b10feb4d88f8d35d0c7ffd0b75d4fbc8f` merged into `v7-dev` at `547ab20bf2d92083bc800cf294087cf3ddf4efcb`; pre-merge checks passed 24/24 after one approved Windows 3.12 rerun; post-merge checks passed 13/13 with CodeQL 3/3; independent review P0/P1/P2 = 0; exact twelve-file allowlist; feature branch retained; `main` unchanged |
| V7-10 Durable Local Human Visual Review Evidence | Complete and verified | Completed V7-06 through V7-09, accepted RFC-V7-008, and explicit approval of the exact fourteen-file implementation package | PR #42 final head `ac4d09c1fb9c5ab5dcaf4d96e475bd1044c3f048` merged into `v7-dev` at `3c83a067ece1a1b3d45f89d4816ffb47153f81d8`; full pytest passed (3190 passed / 20 skipped); PR checks passed 10/10 with CodeQL 3/3; post-merge checks passed 10/10 with CodeQL 3/3; independent review P0/P1/P2 = 0/0/0; exact fourteen-file allowlist; feature branch retained; `main` unchanged; I02 remained out of scope |
| V7-11 Safe Local Human Visual Review Evidence History | Complete and verified | Completed V7-08 through V7-10, accepted RFC-V7-009, and explicit approval of the exact fifteen-file implementation package | PR #45 final head `32a0386dce4101606fd1c66e748eef3ffa213e62` merged into `v7-dev` at `7ef060d98b631ed2b9492ee9c3e0b0560c70b08e`; full pytest passed (3215 passed / 20 skipped); PR checks passed 24/24; post-merge CI run #156 passed 10/10 with CodeQL run #59 passing 3/3; independent review P0/P1/P2 = 0/0/0; exact fifteen-file allowlist; feature branch retained; `main` unchanged; I02 remained out of scope |
| V7-12 Durable Local Human Visual Review Evidence-Linked Approval | Complete and verified | Completed V7-07 through V7-11, accepted RFC-V7-010, and explicit approval of the exact twenty-one-file implementation package | PR #48 final head `5835de2c5d890a40a232f1ff7ad9a7a690240eff` merged into `v7-dev` at `a02eedf38cd79c43c2add68ac08c332dab5eefb8`; full pytest passed (3238 passed / 16 skipped); PR CI run #166 passed 10/10 with CodeQL run #65 passing 3/3; post-merge CI run #167 passed 10/10 with CodeQL run #66 passing 3/3; independent review P0/P1/P2 = 0/0/0; exact twenty-one-file allowlist; feature branch retained; `main` unchanged; I02 remained out of scope |
| V7-13 Private Panel-Aware Page Generation Foundation | Complete and verified; public routing disabled | Completed V7-12, accepted RFC-V7-011, and completed Slice 1 through Slice 4 validation | PR #54 merged Slice 4 into `validation/rfc-v7-011-slice-3` at `4719c55a3ade5b3f10f75d4432f07bcbc958d6a0`; PR #55 merged that branch into `v7-dev` at `a760488f43f84e28978fe5b3bf1d25e44b9b8396`; PR #55 CI passed; post-merge CI run `40273044192` passed 10/10 jobs; final independent closure P0/P1/P2 = 0/0/0; release, public activation, live Provider/ComfyUI, and I02 remained out of scope |
| V7-14 Safe Panel-Aware Activation Bridge | Complete and verified; public routing disabled | Completed V7-13 foundation and explicitly approved V7-14 Slices 1–3 | PR #61 merged at `c9b0c27ef1df8104f70b573c9dd7c10266b523df`, PR #62 at `4feeae65cab5a48397f274164422588d4e2f7adc`, and PR #63 at `1daff9e58bd52058e44175c99b4248ea321a30f5`; each PR-head CI passed 24/24; final independent review P0/P1/P2 = 0/0/0; exact seven unique implementation/test files; public activation remains V7-15+; live ComfyUI, I02, `main`, release/publication, dependency/lockfile, schema/migration, and branch deletion remain unperformed and unapproved |
| V7-15 Safe Local Panel-Aware Generation Activation | Slice 1 Complete and verified; public routing disabled | V7-14 complete; RFC-V7-013; separate Slice 1 approval | PR #65 source head `5948562b89bb9fef1823800dc6365578c14e48a4` squash-merged to `v7-dev` at `aa89590498bc145e34db5cc77e1f83008df2e9d3`; PR-head required checks passed 24/24; focused 54 passed / 3 skipped; authority regression 114 passed / 2 skipped; V6 LTS regression 99 passed; full pytest 3464 passed / 25 skipped; independent review P0/P1/P2/OTHER = 0/0/0/0; post-merge CI run #40650264745 passed 10/10 and CodeQL run #40650264438 passed 3/3; source branch retained; at the PR #65 record, Slices 2–3 were unimplemented and unapproved; generic `/generate` unchanged |

No later Epic 1 implementation is authorized solely by this roadmap.
Additional issues must be proposed with their own bounded scope, compatibility
analysis, validation plan, and approval state.

## Epic quality gates

Every Epic 1 change requires architecture-boundary, backward-compatibility,
workflow-invariant, LocalFile security, and delivery-contract review. P0 or P1
findings block merge. Documentation acceptance does not establish release
readiness, and release readiness does not authorize publication.

## V7-14 / V7-15 Private Asset-ID Registration Amendment (2026-10-28)

The documentation/specification amendment was implemented and verified within
V7-15 Slice 1 under PR #65. The V7-14 completion/merge/CI/review record above
remains historical evidence for V7-14; PR #65 provides separate V7-15 Slice 1
evidence. Slice 1 is complete; public routing remains disabled.

The amendment in RFC-V7-012 and RFC-V7-013 requires the server-derived canonical
`panel-asset-v7-014-*` to be the exact LocalDurableAssetOwner registry asset ID
on the dedicated private V7-14 registration path. Legacy V7-04 keeps
`asset-generated-*`. ID mismatch, tamper, another ID for the same attempt and
cross-attempt ID reuse fail closed; no alias mapping, record relabeling or
migration is permitted. Exact replay, at-most-once, Page fence, mode rechecks
and no provider fallback/retry remain mandatory. Canonical derivations and
existing mode equality checks remain unchanged.

The exact six implementation/test files listed in RFC-V7-013 were delivered
with the three approved docs/specification files, nine files total. This
completion record authorizes no further source/test changes, tests, public
API/Web, generic `/generate`, schema/migration, dependency/lockfile, I02, live
ComfyUI, `main`, branch/Git operations, release/publication, or package
publication. Slices 2 and 3 require separate exact allowlists and explicit
approval before implementation.
