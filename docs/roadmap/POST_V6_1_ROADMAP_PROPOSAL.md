# Post-v6.1 Roadmap Proposal

## Status

Active. Option A continues to govern v6 LTS maintenance. The product objective
below was implemented as verified POST-v6.1 I01–I06 readiness work in commits
`4039322` through `9d596bd`. This document records that pre-release evidence;
it does not authorize a version, dependency, release, or subsequent I02 change.

## Established baseline

- v6.0 is the stable Platform API, SDK, Extension API, and Marketplace
  Specification baseline.
- v6.1 Epic 3 is closed by the approved decision to retain the existing v6
  Analytics and Observability reports without a new Portfolio or Enterprise
  runtime contract.
- The v6 architecture retains one-page workflow execution, StateMachine-owned
  transitions, persisted-storyboard-before-generation, and
  review-before-approval boundaries.

## Repository evidence

- `docs/ROADMAP_V6.md` identifies the v6 platform implementation sequence but
  does not define a post-v6.1 Epic, objective, input, output, or acceptance
  criteria.
- `docs/V6_LTS_PLAN.md` and `docs/V6_LTS_POLICY.md` limit v6 maintenance to
  compatible correctness, security, documentation, validation, and performance
  work.
- `docs/TECHNICAL_DEBT_REGISTER.md` records only owner-controlled or external
  follow-up; it explicitly does not authorize implementation work.
- `docs/PLATFORM_BLUEPRINT.md` defines platform boundaries and sequencing, not
  an unselected future product contract.

## Current roadmap decision

Option A is approved. The active roadmap is v6 LTS maintenance under
`docs/V6_LTS_PLAN.md`. No source-backed local maintenance Issue is currently
open. Do not convert deferred external work, generic architecture labels, or
prior-version DTOs into a new implementation scope.

## Product Owner options

### A. Continue v6 LTS maintenance (recommended)

Accept only a reproducible bug, regression, security, compatibility, or
measured performance Issue under the existing v6 LTS policy.

### B. Define a new compatible product objective

Provide the problem, caller-visible outcome, input/output boundary, affected
users, and acceptance criteria. Planning may then determine whether an
additive v6.x scope is supported.

### C. Start a future major-version discovery phase

Define the target version and product objective before architecture or
implementation work. No public-contract or execution change is implied.

## Decision required before a new Epic

Option A requires no new Epic. For B or C, record the product objective and
acceptance criteria before creating an Epic or Issue.

## Approved design objective: POST-V6.1-I01

### Title

Read-only project page readiness inspection through the existing project-status
query.

### Design and authorization status

- Product objective: **APPROVED**.
- Planning and architecture review: **APPROVED FOR THIS DOCUMENTATION PHASE**.
- Public-contract verification: **VERIFIED** by the committed compatibility
  suite and v6.0 baseline comparison.
- Implementation: **COMPLETED AND VERIFIED** as POST-v6.1 I01–I06 readiness
  work; no further implementation authority is granted here.
- Release: **NOT AUTHORIZED**.

`POST-V6.1-I01` is a bounded issue identity within this proposal. It creates no
new Epic, version, public command, endpoint, layer, or implementation authority.

### Planning draft

This section is the complete repository-backed Planning Draft for the approved
objective. Its fields, allowlists, and acceptance matrix are frozen for the
subsequent explicit implementation decision.

### Issue specification

- Issue: `POST-V6.1-I01`.
- Architecture owner: `ProjectWorkflowEngine` for the read-only projection,
  with route ownership retained by the existing generic and LocalFile durable
  coordinators and next-operation authority retained exclusively by
  `StateMachine`.
- Existing caller surface: the coordinator `project_status` contract, implemented
  by `WorkflowCoordinator` and `LocalFileDurableWorkflowCoordinator`, shared by
  CLI `project status` and MCP `get_project_status`.
- Change type: additive, read-only project-status projection.
- Risk: medium because the default LocalFile status route currently persists,
  runtime construction currently creates both configured Provider adapters,
  and the result DTO is observable through CLI and MCP.
- Implementation status: completed and verified in the committed POST-v6.1
  I01–I06 readiness checkpoints.

### Objective

When a user inspects an existing manga project, report for every persisted Page
its current state, unmet prerequisites, and exactly one next operation, or one
explicit terminal/blocked no-op outcome. The query must not generate an image,
construct or call an external Provider, change workflow state, or persist any
data.

### Scope

- Reuse the existing project-status application query surfaced by
  `WorkflowCoordinator.project_status`, CLI `project status`, and MCP
  `get_project_status`; add no command or endpoint.
- Keep `ProjectWorkflowEngine` as the aggregate-reporting owner and
  `StateMachine` as the sole owner of the legal next command.
- Add a typed, deterministic per-Page inspection projection to the existing
  project-status response. Preserve every existing project-status field and
  call form.
- Inspect all persisted Pages in ascending `page_number` order.
- Validate persisted stage evidence cumulatively through the Page's declared
  state. Dialogue and continuity remain optional support artifacts.
- Treat structurally malformed Project data as a query failure. Treat a
  structurally valid Page whose declared state is inconsistent with persisted
  stage evidence as blocked, with the missing evidence reported and no
  executable command exposed.

### Inputs

- Existing `project_id` accepted by the current project-status query.
- One Project loaded through the existing `ProjectRepository` port.
- The Project's persisted Pages, Page states, and stage artifacts.
- The existing `StateMachine` transition and command mapping.

No caller-supplied state, prerequisite, next command, Provider, image adapter,
or execution authorization is an input.

### Outputs

The existing project-status response, with one deterministic inspection entry
per persisted Page. Each entry contains:

- `page_number`;
- `current_state`;
- ordered `unmet_prerequisites`;
- exactly one outcome: the `StateMachine` command, `NO_OP_TERMINAL`, or
  `NO_OP_BLOCKED`;
- an explicit non-execution marker.

No output is an execution capability or workflow authorization.

### Persisted evidence rules

The cumulative evidence required by each declared state is:

| Declared state | Required persisted Page fields |
| --- | --- |
| `Draft` | none |
| `Designed` | `page_design` |
| `Reviewed` | `page_design`, `review` |
| `Storyboarded` | `page_design`, `review`, `storyboard` |
| `PromptBuilt` | `page_design`, `review`, `storyboard`, `prompt` |
| `Generated` | `page_design`, `review`, `storyboard`, `prompt`, `image` |
| `QualityChecked` | `page_design`, `review`, `storyboard`, `prompt`, `image`, `quality` |
| `Approved` | `page_design`, `review`, `storyboard`, `prompt`, `image`, `quality`, `approval` |

For a consistent non-terminal Page, the sole next operation is
`StateMachine.next_command(current_state)`. A consistent `Approved` Page emits
`NO_OP_TERMINAL`. Any missing cumulative evidence emits `NO_OP_BLOCKED`, never
an executable command. The inspection must not infer completion from history,
metadata, filenames, Provider state, or caller assertions.

### Acceptance criteria

1. The query loads one existing Project and returns one inspection entry for
   every persisted Page, ordered by ascending page number.
2. Each entry reports the exact persisted `Page.state`, the exact ordered set
   of missing cumulative stage fields, and exactly one operation/no-op outcome.
3. A consistent non-terminal Page obtains its sole command from the existing
   `StateMachine`; a consistent `Approved` Page is terminal.
4. Inconsistent Page state/artifact combinations fail closed as
   `NO_OP_BLOCKED`. Structurally malformed Project data fails the query through
   the existing validation/error boundary.
5. Repeating the query against identical repository bytes returns identical
   JSON data and ordering.
6. The query calls repository `load` only. It calls no `save`, delete, event
   publication, Agent, workflow execution, StateMachine transition validation,
   image generator, Provider factory, Provider constructor, network client, or
   external process.
7. Repository bytes, Page state, artifacts, metadata, history, events, and
   timestamps are unchanged after both CLI and MCP project-status queries.
8. Existing project-status fields and call forms remain valid; no root export,
   command name, option, MCP tool name, endpoint, dependency, schema, or
   migration changes.
9. Mandatory one-Page, forward-only, persisted-storyboard-before-generation,
   and completed-quality-review-before-approval invariants remain unchanged.
10. Focused, CLI, MCP, StateMachine, frozen-v6, LTS compatibility, static, and
    full regression gates pass before completion is claimed.

### Out of scope

- Running, resuming, scheduling, or approving any workflow step.
- Image generation, image retrieval, asset mutation, Provider discovery,
  Provider selection, Provider construction, credentials, network calls, or
  external processes.
- Project normalization persistence, repair, migration, import/export, or
  repository mutation.
- New CLI commands/options, MCP tools/resources, FastAPI routes, SDK/Plugin
  exports, root exports, StateMachine states/transitions, or public execution
  contracts.
- IMP-11, CEOS I02 Slice 2/3, Astra migration/pilot #2, and R26 remediation.

### Dependencies

- `Project`, `Page`, and persisted stage fields in `domain/project.py`.
- `StateMachine.next_command` and terminal-state behavior in
  `domain/state_machine.py`.
- Existing `ProjectRepository.load`, `ProjectWorkflowEngine`, `ProjectContext`,
  and `WorkflowCoordinator.project_status` ownership.
- Existing CLI `project status` and MCP `get_project_status` delivery adapters.
- Frozen v6.0 artifacts and V6/LTS compatibility tests.

### Architecture notes

`ProjectWorkflowEngine` is the single best existing owner because it already
owns Project aggregate reporting and receives only the repository port and
event interface. The Page `StateMachine` remains the sole source of legal next
commands; the project owner may only project its answer and must not duplicate
the transition table. `WorkflowCoordinator.project_status` remains a thin
delegate, and CLI/MCP remain presentation adapters. No new layer is introduced.

The existing project-status implementation persists normalized position. This
issue must add a distinct read-only inspection path and route the status query
through it; it must not silently reuse a path that calls repository `save`.
Existing mutation-oriented lifecycle operations remain unchanged.

The implementation preflight established two default-path facts that refine
the frozen design. For a LocalFile repository, `build_runtime` selects
`LocalFileDurableWorkflowCoordinator`; its `project_status` override currently
uses `_mutate(ProjectStatusMutation(...))`, so the generic coordinator is not
the effective CLI/MCP owner. The corrected LocalFile flow is therefore
`build_runtime` -> `build_localfile_durable_workflow` ->
`LocalFileDurableWorkflowCoordinator.project_status` -> the coordinator's
existing private `ProjectWorkflowEngine` -> the new read-only inspection
operation. The generic flow remains `WorkflowCoordinator.project_status` ->
the same inspection operation. Durable `run`, `resume`, lifecycle, batch, and
conditional-commit routes remain unchanged.

The same preflight established that `build_runtime` eagerly calls both
`ImageGeneratorFactory.create` and `LLMFactory.create` before any command is
dispatched. A router-only fix therefore cannot satisfy the frozen zero-
construction gates. The runtime composition root must validate the configured
adapter names without construction and provide private lazy protocol adapters
that instantiate the selected implementation only on the first workflow
`generate` call. This preserves fail-fast configuration-name validation,
configured-provider selection, Agent and `WorkflowEngine` contracts, and all
execution behavior while allowing both CLI and MCP status inspection to build
their normal runtime without constructing either Provider. No public lazy
adapter type or factory contract is added.

MCP already receives the exact `runtime.coordinator` through
`build_mcp_server`, and `MangaApplicationService.get_project_status` already
delegates to that coordinator. The second composition review below corrects
the earlier conclusion that MCP composition itself required no change.
`cli/app.py`, MCP application, contracts, registry, and resources still require
no change.

### Second composition-remediation addendum

The complete normal LocalFile construction trace, starting with an existing
Project and no durability sidecars, is:

| Surface and step | Pre-status behavior | Remediation/constraint |
| --- | --- | --- |
| CLI `load_config` and `configure_logging` | Reads configuration or in-memory defaults and configures stream logging; `project status` does not request config creation | No change |
| `PluginManager.load_enabled` / shutdown | Discovers local manifests and may import, initialize, and stop explicitly enabled extension code; with no enabled plugins it performs no external action | Acceptance fixture has no enabled plugins; third-party plugin lifecycle remains outside this first-party status guarantee |
| Adapter registration and configured-name validation | Registry-only; validation must not call either adapter factory | Keep fail-fast built-in/plugin name validation after registration |
| Lazy image/LLM protocol adapters, prompt/Agent graph, `MemoryEventBus`, `StateMachine`, and `WorkflowEngine` | In-memory construction only; no adapter construction, generation, publication, network, or process start | Retain the first remediation's private lazy adapters |
| `ProjectLoader.from_settings` -> `LocalFileRepository` -> `LocalFileRevisionStore` | Stores paths and collaborators only for the LocalFile branch | No change; database-provider schema creation is not on this LocalFile path |
| `build_localfile_external_generation_composition` | Eagerly constructs the Ledger, receipt, R18/R25/R30 and asset-delivery graph and creates seven SQLite sidecars before CLI status | In `cli/runtime.py`, replace eager construction with a private lazy composition/quality-gate proxy; resolve the unchanged builder only on the first execution operation that needs it |
| `build_localfile_durable_workflow` | Constructs in-memory coordinator, worker, scheduler, mutation adapters, and event factory; it performs no mutation or publication until an execution method is called | Keep unchanged; inject the lazy quality-gate proxy |
| CLI `project_status` | Delegates durable coordinator -> read-only `ProjectWorkflowEngine.status` -> one repository `load` | No save, revisioned load, event publication, Agent, gate, Provider, network, or process call |
| `_mcp_server` -> `build_mcp_server` | Independently calls `build_localfile_quality_ledger_gate`, whose store constructor creates the workflow Ledger SQLite sidecar before `get_project_status` | In `mcp/composition.py`, inject a private lazy `LogicalOutputAssetQualityGatePort` proxy; construct the unchanged gate only if an execution tool calls `require_applied` |
| MCP service, tool registry, resources, prompts, and server | Constructors retain injected objects/callables only; diagnostic Providers are not invoked while registering tools | No change |
| MCP `get_project_status` | Registry handler -> `MangaApplicationService.get_project_status` -> injected coordinator read-only status path | Same load-only and zero-event/execution constraints as CLI |

An isolated full-root reproduction confirmed the trace. CLI runtime construction
created these files below `projects/_durability` before status, while the status
call created none:

- `_workflow_application_ledger/workflow-application-ledger.sqlite3`;
- `_workflow_application_ledger/durable-application-commit-receipts.sqlite3`;
- `_post_cas_application_attestations/post-cas-application-attestations.sqlite3`;
- `_r30_pre_cas_ledger_provenance/r30-pre-cas-ledger-provenance.sqlite3`;
- `_next_generation_normal_execution/assets/registry/asset-owner.sqlite3`;
- `_next_generation_normal_execution/assets/_durability/_post_lts_real_asset_delivery/real-asset-delivery.sqlite3`;
- `_next_generation_normal_execution/assets/_durability/_post_lts_real_delivery_binding/real-delivery-binding.sqlite3`.

An independently composed LocalFile MCP server created only the workflow
application Ledger database during `build_mcp_server`; `get_project_status`
then created nothing. Consequently `mcp/composition.py` is the sole additional
source file required beyond the first remediated allowlist. No quality-gate,
Ledger, receipt, R18/R25/R30, Provider, repository, MCP registry, or other
durability implementation may be modified. Private proxies in the two existing
composition roots preserve the current builders, their object graph, and their
first-use execution semantics without introducing a public contract.

The response change is additive, but `ProjectContext` and project-status JSON
are observable subpackage/CLI/MCP contracts. The implementation-time artifact
comparison and selected compatibility tests verified the public-contract
boundary for the committed I01–I06 readiness work. This historical record does
not self-authorize a further expansion.

### Exact implementation allowlist

Source files permitted for the completed implementation:

- `src/manga_director/workflow/hierarchy_contracts.py`
- `src/manga_director/workflow/project_engine.py`
- `src/manga_director/workflow/coordinator.py`
- `src/manga_director/workflow/localfile_durable_routing.py`
- `src/manga_director/cli/runtime.py`
- `src/manga_director/mcp/composition.py`

Focused tests permitted for the completed implementation:

- `tests/unit/test_project_workflow.py`
- `tests/integration/test_project_cli.py`
- `tests/unit/test_mcp_server.py`
- `tests/test_localfile_durable_routing_activation.py`
- `tests/integration/test_mcp_cli.py`

Compatibility tests are validation-only and must not be edited:

- `tests/unit/test_state_machine.py`
- `tests/unit/test_public_api.py`
- `tests/unit/test_image_adapters.py`
- `tests/unit/test_llm_adapters.py`
- `tests/test_localfile_external_generated_application.py`
- `tests/test_future_real_delivery_r25_normal_materialization.py`
- `tests/test_localfile_private_real_delivery_composition.py`
- `tests/test_r28_private_publication.py`
- `tests/test_v6_lts.py`
- `tests/test_v6_lts_baseline.py`
- `tests/test_v6_lts_compatibility.py`
- `tests/test_v6_lts_security_evidence.py`

Implementation-synchronized documentation allowlist:

- `docs/project_workflow.md`
- `docs/PUBLIC_API.md`

No other source, test, configuration, dependency, lockfile, generated artifact,
or documentation file is authorized by this planning set. In particular, the
following protected dirty files are excluded and must remain byte-identical:

- `src/manga_director/mcp/contracts.py`
- `src/manga_director/mcp/registry.py`
- `src/manga_director/mcp/resources.py`
- `src/manga_director/repositories/local_file.py`
- `tests/test_security_localfile_project_path_containment.py`

### Validation

The completed implementation was verified in this order:

1. Focused Page/project inspection unit tests.
2. LocalFile durable-routing, runtime/provider/sidecar laziness, CLI, and MCP
   status tests, including a zero-sidecar full-root manifest comparison.
3. Existing image/LLM runtime-selection, external-generation composition,
   StateMachine, and public-contract tests.
4. Frozen-v6 and V6/LTS tests.
5. Ruff on the affected files, strict mypy, and full pytest.
6. A v6.0 sdist/wheel comparison for affected exports, call forms, DTO fields,
   and JSON response compatibility.

The implementation and runtime tests were executed for the committed I01–I06
readiness work. Their results are release evidence only; they do not authorize
a new change, version, or release.

### Estimated complexity

Medium. The computation is bounded and read-only, but the effective LocalFile
status path had a persistence side effect, two composition roots eagerly build
durability sidecars, runtime adapter construction must remain lazy, and the
additive project-status DTO is observable through both CLI and MCP. The final
remediation remains closable in one cycle: only composition-local single-method
proxies are added, while every durable builder/store, delivery adapter, and
public factory contract remains unchanged.

### Frozen executable acceptance matrix

| Gate | Executable proof | Required result |
| --- | --- | --- |
| Every Page and deterministic order | Focused unit test with unsorted multi-Page input; invoke twice and compare `model_dump(mode="json")` | One entry per Page, ascending page number, byte-equivalent JSON on repeat |
| Current state | Parameterized unit test for every `PageState` | Entry state equals persisted state exactly |
| Unmet prerequisites | Parameterized cumulative-field matrix plus one missing-field case for every state | Exact ordered missing-field tuple; no inference from metadata/history |
| Exactly one next outcome | Parameterized matrix for all states and inconsistent variants | One StateMachine command, `NO_OP_TERMINAL`, or `NO_OP_BLOCKED`; never zero or multiple outcomes |
| Read-only repository | Repository spy whose `save`, `delete`, and mutation methods raise; compare loaded Project before/after | Load succeeds; all mutation calls remain zero; Project objects equal |
| Effective LocalFile route | Build the normal LocalFile runtime; invoke `runtime.coordinator.project_status` with `_mutate`, `ProjectStatusMutation`, `_conditional_commit`, and EventBus publication spies set to raise | Status delegates to the read-only `ProjectWorkflowEngine` inspection; no durable mutation primitive is reached |
| Generic/LocalFile parity | Run the same multi-Page Project through generic and LocalFile coordinators | Inspection JSON is identical and deterministically ordered |
| CLI/MCP byte preservation | Run existing CLI `project status` and MCP `get_project_status` against a LocalFile fixture; hash the project file tree before/after | Hash manifest unchanged |
| Zero workflow mutation | EventBus/Agent/engine execution spies raise on use; compare Page state, artifacts, metadata, history, events, and timestamps | No call and no value changes |
| Runtime construction is inspection-safe | Patch `ImageGeneratorFactory.create` and `LLMFactory.create` to raise; build the normal LocalFile runtime and invoke CLI and MCP project status | Runtime and both status surfaces succeed; both factory calls remain zero |
| Exhaustive construction proof | Start from an existing valid LocalFile Project under an otherwise empty config/repository root with no enabled plugins or sidecars; patch adapter factories, external-generation/quality-gate builders, repository mutation methods, EventBus publication, network clients, sockets, and subprocess launchers to record/raise as appropriate; hash every file under the full root before runtime build, after CLI status, after MCP server build, and after `get_project_status` | Both status results succeed and match; no patched constructor/action is reached; all four full-root manifests are byte-identical; no SQLite, journal, receipt, revision, index, page-document, log, temp, lock, or asset file appears |
| Deferred sidecar compatibility | With recording wrappers, invoke the first legal execution operation that requires the LocalFile quality gate through CLI and MCP | Each unchanged builder resolves at most once per composition, only at first use; the established Ledger/R18/R25/R30 object graph and durable execution results remain unchanged |
| Deferred execution compatibility | Build the runtime with recording factory builders, perform one image/LLM-backed workflow execution, and run the existing adapter runtime-selection tests | Each selected adapter is constructed on first use, not at runtime build, and existing execution results are unchanged |
| Zero image generation | Image-generator factory/adapter spies raise on construction or call during runtime build and status inspection | No construction and no call |
| Zero external Provider activity | LLM factory/adapter/network/process spies raise on construction or call during runtime build and status inspection | No construction, network, subprocess, or external call |
| Malformed/inconsistent fail-closed | Malformed serialized Project fixture plus valid models missing each cumulative field | Malformed load raises existing typed error; inconsistent Pages emit only `NO_OP_BLOCKED` |
| V6 compatibility | `pytest tests/unit/test_state_machine.py tests/unit/test_public_api.py tests/test_v6_lts.py tests/test_v6_lts_baseline.py tests/test_v6_lts_compatibility.py tests/test_v6_lts_security_evidence.py` plus v6.0 artifact comparison | All pass; no removed/renamed export, changed call form, required parameter, command/tool name, or incompatible DTO field |
| Focused delivery | `pytest tests/unit/test_project_workflow.py tests/test_localfile_durable_routing_activation.py tests/integration/test_project_cli.py tests/integration/test_mcp_cli.py tests/unit/test_mcp_server.py tests/unit/test_image_adapters.py tests/unit/test_llm_adapters.py` | All pass, including generic/LocalFile parity, provider and sidecar laziness, full-root byte preservation, deferred execution compatibility, additive fields, and unchanged existing fields |
| Static/full regression | Ruff on the exact source/test allowlist, strict mypy, then full `pytest` | All applicable checks pass with no weakened exclusion |

### Design decision

The twice-remediated design is **PASS**. The owner, effective LocalFile and
generic flows, provider- and sidecar-laziness boundaries, caller surface,
inputs, outputs, compatibility boundary, final allowlists, and acceptance matrix
were implemented and verified in the committed I01–I06 readiness checkpoints.
This record grants no new implementation authority and does not authorize I02.

## Retained boundaries

- Do not weaken existing v5.x or v6.0 public contracts.
- Do not add Repository discovery, persistence, remote services, Provider
  calls, or external operations without a separately approved architecture.
- Do not change WorkflowEngine or StateMachine ownership, or the one-page,
  storyboard, and quality-review invariants.
