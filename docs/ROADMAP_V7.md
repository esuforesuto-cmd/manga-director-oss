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

## V7-05 — Live ComfyUI Local Verification Gate

### Design and completion status

Complete and verified. The bounded live-verification contract is frozen by
[RFC-V7-004: Live ComfyUI Local Verification Gate](RFC_V7_004_LIVE_COMFYUI_LOCAL_VERIFICATION.md).
The RFC records the verified contract after the completed run and does not
authorize another live request or new implementation.

### Objective

Prove exactly once that the V7-04 ComfyUI Local Provider can execute against a
real loopback-only ComfyUI installation and carry one PromptBuilt Page through
durable admission, fixed-graph preparation, one Provider start, bounded result
observation, strict PNG validation, LocalFile asset registration, and the
existing legal transition to Generated without weakening public, workflow,
persistence, security, or compatibility boundaries.

### Frozen live gate

- one explicitly authorized, dedicated Project and one PromptBuilt Page;
- exact repository commit, loopback endpoint, checkpoint, Provider, Page, and
  human authorization evidence fixed before execution;
- read-only repository, listener, health, core-node, checkpoint, Project, and
  prior-attempt preflight before any external side effect;
- six required core node types from `python_module = nodes` and no custom
  nodes, installs, model downloads, arbitrary workflow JSON, or scripts;
- persisted prompt normalization and relative LocalFile root resolution
  without changing stored prompt or existing containment authority;
- fixed graph construction and validation before the durable Provider-start
  boundary is consumed;
- exactly one `POST /prompt`, bounded polling of the same `prompt_id`, one
  same-origin `/view` byte response, one strict PNG, and zero automatic retry;
- ComfyUI 0.40.0 optional descriptor `metadata` and `id` are validated and
  discarded, never used as path, lookup, identity, or asset authority;
- any ambiguous post-start outcome becomes `RECOVERY_REQUIRED` with no
  replacement attempt, fallback, or Provider switch; and
- successful evidence requires attempt `COMPLETED`, generation evidence ready,
  asset registration success, strict PNG PASS, Page `Generated`, and no source
  or staged diff caused by the live run.

### Verified baseline and remediation evidence

The verified environment used ComfyUI 0.40.0 on
`http://127.0.0.1:8188`, an NVIDIA RTX 4070 Ti, and the exact checkpoint
`animagine-xl-4.0.safetensors`. All six required core nodes passed preflight.
The final live E2E issued one `POST /prompt`, performed zero retries, completed
one durable attempt, produced ready generation evidence, registered one asset,
passed strict PNG validation, and moved the dedicated Page to `Generated`.
The operation added no source diff.

Live verification exposed five bounded gaps: relative LocalFile durability-root
resolution, persisted prompt normalization, Provider-start ordering, the
polling window, and ComfyUI 0.40.0 descriptor compatibility. PR #28 corrected
only those gaps and changed exactly this eleven-file allowlist:

1. `src/manga_director/production/next_generation_comfyui_provider_adapter.py`
2. `src/manga_director/production/next_generation_normal_execution_composition.py`
3. `src/manga_director/production/next_generation_provider_adapter_composition.py`
4. `src/manga_director/production/next_generation_provider_invocation.py`
5. `src/manga_director/repositories/project_loader.py`
6. `src/manga_director/workflow/localfile_comfyui_real_image_generation.py`
7. `tests/integration/test_cli.py`
8. `tests/test_localfile_comfyui_real_image_generation.py`
9. `tests/test_next_generation_comfyui_provider_adapter.py`
10. `tests/test_next_generation_provider_adapter_composition.py`
11. `tests/test_next_generation_provider_invocation.py`

Checkpoint commit `e138cdf5b83f8da274051ae8c4028b42f4c60182` was merged
into `v7-dev` by PR #28 as merge commit
`fd58392d919311403a32111ea7a3d2d9628d6ba9`. The 24 required PR checks
passed, and both post-merge workflows (`CI` and `Push on v7-dev`) passed.
Independent final review reported P0 = 0, P1 = 0, and P2 = 0. The checkpoint
branch was retained, and `main` remained unchanged.

### Compatibility and exclusions

V7-05 preserves the public API, DTOs, StateMachine, WorkflowEngine, LocalFile
schema and containment, mock default, legacy deterministic ComfyUI stub,
OpenAI V7-03 behavior, HTTP, Web UI, MCP, SDK, Plugin, dependencies, package
metadata, and v5/v6 compatibility. Optional ComfyUI descriptor fields,
environment facts, checkpoint names, generated PNGs, and live-run artifacts do
not become public or persistent authority.

I02 remains completely independent and out of scope. Another live generation,
source change, dependency or lockfile update, remote endpoint, custom node,
model download, retry, fallback, Provider switch, `main`, versioning, release,
tag, publication, Settings, force push, history rewrite, and branch deletion
require separate authorization.

### Authorization gate

V7-05 is complete. Its prior live-run, remediation, PR, and merge authority is
exhausted. RFC-V7-004 authorizes no additional live call or implementation.
Any future live verification requires a new exact one-attempt approval package
and must stop if code changes or broader scope are required.

## Epic 1 sequencing

| Issue | State | Dependency | Completion evidence |
| --- | --- | --- | --- |
| V7-01 Workflow HTTP Adapter | Complete | Accepted RFC-V7-001 and explicit v7 implementation authorization | PR #17 merged into `v7-dev` at `097a80d`; required CI passed; P0/P1 = 0; `main` unchanged |
| V7-02 Real Local Delivery End-to-End Gate | Complete | Completed V7-01 and explicit approval of the bounded V7-02 Planning Draft | PR #20 merged into `v7-dev`; final head `7d0034a2dad46c6ff982d03104d32d935d5db796`; merge commit `ad671b63a4135997ffc41e8ab95bb8a681668980`; required CI run #69 passed 10/10 jobs; independent review P0/P1/P2 = 0; exact seven-file allowlist; `main` unchanged |
| V7-03 Provider-Neutral Real Image Delivery | Complete and verified | Completed V7-02, accepted RFC-V7-002, and explicit approval of the exact ten-file implementation allowlist | PR #23 merged into `v7-dev` at `b688abb88bf07e7508a806c48f86c27b6e41fa5b`; CI run #82 passed 10/10 jobs; independent review P0/P1/P2 = 0; exact ten-file allowlist; feature branch retained; `main` unchanged |
| V7-04 ComfyUI Local Provider | Complete and verified | Completed V7-03, accepted RFC-V7-003, and explicit approval of the exact twelve-file implementation allowlist | PR #26 merged into `v7-dev` at `abd5a21a2597cb51286b666b23298b5f47450094`; post-merge CI run #95 passed 10/10 jobs; CodeQL run #19 passed 3/3 jobs; independent review P0/P1/P2 = 0; exact twelve-file allowlist; feature branch retained; `main` unchanged |
| V7-05 Live ComfyUI Local Verification Gate | Complete and verified | Completed V7-04 and explicit authorization for one dedicated live attempt; RFC-V7-004 subsequently freezes the verified boundary | Final live E2E used one POST and zero retries; PR #28 checkpoint `e138cdf5` merged into `v7-dev` at `fd58392d`; 24 required checks and both post-merge workflows passed; independent final review P0/P1/P2 = 0; exact eleven-file remediation allowlist; checkpoint branch retained; `main` unchanged |

No later Epic 1 implementation is authorized solely by this roadmap.
Additional issues must be proposed with their own bounded scope, compatibility
analysis, validation plan, and approval state.

## Epic quality gates

Every Epic 1 change requires architecture-boundary, backward-compatibility,
workflow-invariant, LocalFile security, and delivery-contract review. P0 or P1
findings block merge. Documentation acceptance does not establish release
readiness, and release readiness does not authorize publication.
