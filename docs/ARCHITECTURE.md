# manga-director Architecture Design — Phase 9 (v1.0.0)

## Scope

Phase 2 supplied a safe, extensible, headless workflow execution foundation. Phase 3 added stateless commercial manga production agents. Phase 4 added CLI delivery. Phase 5 added Project persistence. Phase 6 completed image adapters. Phase 7 prepared the package for public OSS use. Phase 8 completed the release-candidate review. Phase 9 promotes the unchanged RC1 runtime to v1.0.0 and adds release documentation only.

Included: `WorkflowEngine`, `StateMachine`, `WorkflowContext`, `Agent`/`AgentResult`, `WorkflowResult`, `EventBus`, `MemoryEventBus`, stateless agents, Registry-based image-generator adapters, Markdown prompt templates, CLI, configuration, Project aggregates, repository ports/adapters, serializer, validator, logging, tests, public package exports, examples, CI, and release documentation.

Explicitly excluded: real provider API communication, image downloading, image editing, LoRA, ControlNet, databases, Redis, cloud storage, distributed queues, remote MCP, and external services.

## Public API and library boundaries

The root package exposes the intentional library entry points: `Director`, `WorkflowEngine`, `WorkflowContext`, `Project`, `Page`, `ImageGenerator`, and `Repository`. `ImageResult` and the documented error hierarchy are also public where callers need them. Implementation details remain in subpackages and are not re-exported casually.

`Director` is a small facade over `WorkflowEngine`; `Director.default()` constructs a local mock-backed engine for Python-library quick starts. It does not duplicate workflow logic.

The stable error hierarchy is `MangaDirectorError` with `WorkflowError`, `StateTransitionError`, `RepositoryError`, `ConfigurationError`, `ImageGeneratorError`, `ValidationError`, and `CLIError` branches. Existing specialized exceptions remain subclasses of the appropriate branch for compatibility.

All library code uses standard `logging.getLogger(__name__)`; no library behavior uses `print`.

## OSS quality and release assets

- `README.md` provides installation, architecture, workflow, CLI, Python API, adapters, FAQ, roadmap, contribution, and pre-release guidance.
- `examples/` contains minimal, workflow, custom generator, and repository usage samples.
- `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`, `.gitignore`, and PEP 561 `py.typed` support public distribution.
- `.github/workflows/ci.yml` runs Ruff, mypy, and pytest on Python 3.11 and 3.12.

## Image adapters

`ImageGenerator` exposes only `generate(prompt: str) -> ImageResult`. `ImageResult` contains `success`, `image_path`, `metadata`, `provider`, `elapsed_time`, and `messages`.

`ImageGeneratorFactory` is the sole provider-selection mechanism. It has a registry with `register`, `create`, and `available`; its lookup is dictionary-based rather than a provider-specific conditional chain. Built-in registrations are `mock`, `openai`, and `comfyui`.

- `MockImageGenerator` returns a fixed successful `ImageResult` for tests and local CLI use.
- `OpenAIImageGenerator` and `ComfyUIImageGenerator` return explicit stub results. Their API key handling, HTTP calls, and asset persistence are documented TODO boundaries only.

The runtime reads `default_image_generator` from `config.yaml` and calls `ImageGeneratorFactory.create()`. `ImageAgent` receives the resulting `ImageGenerator`, calls only `generate(prompt)`, and copies the provider-neutral result into its artifact. It never receives or branches on a provider name.

## Project persistence

`Project` is the persisted aggregate. It holds `id`, `title`, `chapters`, `pages`, `characters`, `workflow`, `metadata`, `created_at`, and `updated_at`. Each `Page` holds its page number, current state, all stage artifacts (`page_design` through `approval`), metadata, history, and workflow events.

`ProjectRepository` is the persistence port with `load`, `save`, `exists`, `delete`, and `list`. It contains no workflow or agent behavior. Phase 5 provides:

- `InMemoryRepository` for unit tests
- `LocalFileRepository` for local persistence as one JSON or YAML Project document under `projects/`
- `ProjectSerializer` for aggregate ↔ JSON/YAML conversion
- `ProjectValidator` before every save, validating project ID, state-derived required artifacts, unique positive page numbers, and required aggregate fields

`ProjectLoader` maps a persisted Page to/from `WorkflowContext`; it does not decide transitions or call agents. Thus closing and reopening the CLI restores state, artifacts, metadata, history, and events exactly as persisted.

## CLI delivery

The Typer CLI exposes `init`, `design`, `review`, `storyboard`, `dialogue`, `prompt`, `generate`, `quality`, `continuity`, `approve`, `run`, and `status`.

Command handlers do not import or call agents, state-machine methods, or concrete repository classes. They load one `WorkflowContext` through `ProjectLoader`, call a `WorkflowEngine` method, save the returned context, and render the result. The composition root builds the engine and registers agent/adapters before commands run.

- Primary commands call `WorkflowEngine.execute_command()`, which validates the command through `StateMachine` before selecting its agent.
- `dialogue` and `continuity` call `WorkflowEngine.execute_support()`; they add a support artifact and history entry without altering the fixed workflow state.
- `run` calls only `WorkflowEngine.run()`, which advances automatic stages through `QualityChecked`. It deliberately does not approve a page; `approve --approved-by …` remains explicit.
- `status` calls `WorkflowEngine.status()` and displays current state, current step, completed steps, executable step, and workflow history.

## Configuration and project loading

`config.yaml` supports `default_image_generator`, `prompt_directory`, `log_level`, and `repository` settings. The repository setting includes the `local_file` driver, root, and `json`/`yaml` format. `ProjectLoader` depends on the `ProjectRepository` protocol; CLI command handlers do not depend on `LocalFileRepository`.

The `project` command group exposes `create`, `open`, `list`, `delete`, `export`, and `import`. Export/import use `ProjectSerializer` based on a `.json`, `.yaml`, or `.yml` suffix and never overwrite an existing project ID.

The CLI configures standard-library logging at the requested level and logs workflow start, completion, state transitions, and exceptions. Expected errors are printed concisely and return exit code `1`.

## Fixed state machine

```text
Draft → Designed → Reviewed → Storyboarded → PromptBuilt
      → Generated → QualityChecked → Approved
```

`PageState` is an enum. `StateMachine.next_state(current)` returns the one allowed successor. `StateMachine.validate_transition(current, candidate)` raises `InvalidPageTransition` unless the candidate is exactly that successor. `Approved` is terminal. There are no reverse, skipped, or same-state transitions.

## Execution flow

```text
WorkflowContext
       |
       v
WorkflowEngine --asks--> StateMachine.next_state()
       |                         |
       |                         v
       +--> registered Agent for the next state
                 |
                 v
             AgentResult
       |
       +--> StateMachine.validate_transition()
       +--> append artifact/event to WorkflowContext
       +--> EventBus.publish()
       |
       v
WorkflowResult
```

`WorkflowEngine` only reads the current state, determines the one executable agent, runs that agent, validates and updates the state, and publishes events. It does not persist pages, coordinate multiple pages, or let agents invoke one another.

## Shared contracts

### WorkflowContext

The immutable Pydantic context is the only input shared across a workflow step:

- `page`: caller-supplied page data
- `state`: current `PageState`
- `events`: prior `WorkflowEvent` values
- `artifacts`: outputs keyed by completed state
- `metadata`: caller-supplied execution metadata

After a successful step, `WorkflowContext.advance()` returns a new snapshot containing the new state, events, and artifact. ProjectLoader persists that snapshot through the repository protocol outside the engine.

### Agent and AgentResult

```python
class Agent(Protocol):
    def execute(self, context: WorkflowContext) -> AgentResult: ...
```

Every agent returns the same Pydantic `AgentResult`: `success`, `state`, `payload`, `events`, and `messages`. `BaseAgent` is an ABC, and PageDesignAgent, EditorAgent, StoryboardAgent, DialogueAgent, PromptAgent, ImageAgent, QualityAgent, ContinuityAgent, and ApprovalAgent derive from it.

Agents are stateless: they do not update `WorkflowContext`, publish events, or call one another. They transform their supplied context into an `AgentResult`. `WorkflowEngine` remains the only runtime component that calls an agent, validates its target state, advances the context, and publishes events.

### Agent responsibilities

| Agent | Output / responsibility |
| --- | --- |
| PageDesignAgent | Page type, purpose, reader emotion, featured character, big moment, hook, panel count, and panel roles. |
| EditorAgent | Purpose, information, character, direction, and hook checks with improvements. |
| StoryboardAgent | Panels with composition, camera, characters, background, expression, action, dialogue, sound effect, and balloon position. |
| DialogueAgent | Concise, readable dialogue refinements. |
| PromptAgent | Markdown-rendered image prompt from the `prompts/` template. |
| ImageAgent | Adapter invocation only; it owns no image-generation implementation. |
| QualityAgent | Ten 0–5 scores; any score below 4 yields `passed: false`. |
| ContinuityAgent | Character, costume, props, time, location, and emotion mismatch warnings. |
| ApprovalAgent | Validates human approval evidence only; the engine performs the transition. |

### Image-generator adapter boundary

`adapters/image_generator.py` provides the `ImageGenerator` protocol and `ImageGenerationRequest`. It has no provider implementation. `ImageAgent` delegates a rendered prompt to this port and returns the asset reference supplied by the adapter.

### WorkflowResult

One engine execution returns a `WorkflowResult` containing `current_state`, `completed_step`, `events`, `logs`, and the resulting `context` snapshot for the caller's next step.

## Events

`EventBus` is a protocol with `publish(events)` and `subscribe(event_type, handler)`. `MemoryEventBus` is the in-process implementation. Its event types are:

- `PageDesigned`
- `PageReviewed`
- `StoryboardCreated`
- `PromptBuilt`
- `ImageGenerated`
- `QualityPassed`
- `QualityFailed`
- `PageApproved`

The engine emits the event associated with each accepted state. For the quality step, an agent payload of `{"passed": false}` emits `QualityFailed`; otherwise it emits `QualityPassed`. The state still records that the quality step completed as `QualityChecked`.

## Verification

The suite verifies the exact transition table, terminal-state handling, invalid transition rejection, agent selection, event publication/subscription, `AgentResult` shape, workflow result content, failed quality event selection, config loading, CLI status/run/error exits, repositories, serializer, validator, project aggregates, Import/Export, and persisted workflow resumption.

## Implementation self-review

| Architecture commitment | Implementation check |
| --- | --- |
| Fixed, forward-only enum state machine | `domain/state_machine.py` has exactly seven successor mappings; terminal `Approved` raises. |
| Engine owns state validation and agent selection | `workflow/engine.py` calls `next_state()`, selects one agent by resulting state, then calls `validate_transition()`. |
| No agent-to-agent calls | The engine has the only agent registry; the `Agent` protocol exposes only `execute(context)`. |
| Shared typed context and results | `WorkflowContext`, `AgentResult`, and `WorkflowResult` are Pydantic models with the required fields. |
| EventBus interface with Memory implementation | `events/bus.py` defines both `EventBus` and synchronous `MemoryEventBus`, including `publish()` and `subscribe()`. |
| Stateless agents | All nine agents derive from `BaseAgent`; no agent mutates context, publishes an event, or imports/calls another agent. |
| Prompt template management | `PromptAgent` loads `prompts/image_prompt.md` through package resources rather than embedding the template. |
| Image generation boundary | `ImageAgent` calls only `ImageGenerator.generate(prompt)` and consumes `ImageResult`; Factory Registry selection happens outside the agent. |
| Provider extensibility | Factory tests cover built-in discovery, registration, creation, the fixed mock result, config-driven Factory selection, and ImageAgent delegation. |
| CLI has no workflow logic | Command-to-state validation, support execution, run loop, and status derivation are methods of `WorkflowEngine`; handlers delegate to them. |
| Repository boundary | CLI commands use `ProjectLoader`; only its composition factory selects the local-file adapter through the `ProjectRepository` protocol. |
| Aggregate persistence | Local files contain Project/Page state, artifacts, metadata, history, and events; the serializer and validator remain separate from the repository. |
| Logging and failures | CLI configures standard `logging` and converts domain/configuration failures into exit code `1`. |
| Phase 6 exclusions | At Phase 6, source had no real provider API calls, downloads, editing, LoRA, ControlNet, database, Redis, cloud storage, FastAPI, plugin, MCP, or GUI implementation. Later delivery layers are reviewed independently. |
| Public package boundary | Root `__all__` contains documented user-facing types only; `Director` delegates instead of reimplementing the engine. |
| Error and logging boundary | Stable exception branches are exported for consumers; library modules use named standard-library loggers without printing. |
| Publishability | Packaging metadata, license, changelog, contribution guide, examples, GitHub Actions CI, and release checklist are present. |

## v1.0.0 architecture review

The final review confirmed the following with no implementation difference:

- Domain depends only on domain models, errors, and Pydantic; it does not import workflow, agents, CLI, adapters, or repositories.
- Workflow depends inward on domain/event ports; agents and CLI depend on workflow rather than duplicating transition logic.
- `ProjectRepository` contains persistence operations only. `ProjectLoader` is the outer mapping layer between persisted Pages and `WorkflowContext`.
- Adapter selection is isolated in `ImageGeneratorFactory`; agents, workflow, and CLI do not branch on providers.
- CLI command handlers delegate transition, run, support, and status decisions to `WorkflowEngine`.
- Root-level public exports are deliberate; internal construction, provider, serializer, and local-file details stay in subpackages.

No implementation difference from the reviewed RC1 architecture was found after the v1.0.0 test, static-analysis, example, and wheel checks.

## v1.0.0 OSS self-review

| Area | Score (out of 5) | Review |
| --- | --- | --- |
| Architecture | 4 | Clear domain/workflow/agent/adapter/repository boundaries with a small, intentional outer mapping layer. |
| API Design | 4 | Stable root-level exports and structured errors keep common integrations small and explicit. |
| Workflow | 5 | Strict state transitions, single-page operation, and explicit approval preserve the intended invariants. |
| Maintainability | 4 | Typed models, focused modules, CI, and contributor guidance support safe changes. |
| Testability | 5 | In-memory adapters, deterministic mock generation, unit/integration coverage, and static checks are in place. |
| Documentation | 5 | README, release notes, architecture record, v2 roadmap, examples, changelog, license, and contribution guide cover users and contributors. |
| OSS readiness | 5 | v1.0.0 has package metadata, CI, release assets, a verified wheel, and final release checklist. |

Suggested post-v1 improvements (not part of v1.0.0):

1. Add real OpenAI and ComfyUI adapters with credential handling and contract tests.
2. Add a Project schema-version and migration policy before long-lived format changes.
3. Add coverage reporting and an explicit minimum threshold to CI.

## Phase 11 plugin architecture review

The local Plugin System is an outer extension layer. `PluginDiscovery`,
`PluginLoader`, `PluginManager`, and `PluginRegistry` live outside Domain and
Workflow. Plugins can contribute typed Agent, Workflow, Repository,
ImageGenerator, LLM, Prompt, CLI, and EventBus capabilities, but they cannot
alter `PageState`, invoke agents from agents, or bypass `WorkflowEngine`.

The CLI composition root loads enabled local plugins, applies ImageGenerator
builders through the existing factory, and maps declared Agent contributions to
the existing engine mappings. This is the only runtime bridge; the page state
machine and Director remain unchanged. Local manifests are dependency-sorted,
cycles and disabled dependencies are rejected, and shutdown unregisters each
plugin's contributions in reverse order. Remote installation and hot reload are
intentionally excluded.

## Phase 12 LLM adapter architecture review

`LLMProvider` is a generic adapter port, with `LLMFactory` as its only provider selection mechanism. The CLI composition root reads `default_llm_provider`, applies any registered LLM plugin builders, creates one provider, and injects it into the LLM-assisted agents. No agent, workflow component, or CLI command branches on an LLM provider name.

LLM prompt instructions are Markdown assets under `prompts/`; only the rendered request crosses the adapter boundary. Agent assistance is advisory, so a stub or unsuccessful LLM response never changes page-state legality, bypasses a workflow step, or approves a page. Real API calls, streaming, vision, and tools remain outside the implementation.

## Phase 13 prompt-pipeline architecture review

`PromptPipeline` is an application-layer orchestrator for four independently replaceable stages: Builder, Optimizer, Validator, and Renderer. It is the only component that controls their order. PromptAgent calls only the Pipeline and does not import or call an individual stage, template loader, LLM adapter, or image adapter.

Templates are Markdown-only assets loaded through `PromptTemplateLoader`. The pipeline validates page number, purpose, storyboard, character data, template variables, forbidden words, and size before rendering. It is deterministic and does not perform LLM communication, Provider selection, image generation, or state transitions.

## Phase 14 project-workflow architecture review

`ProjectWorkflowEngine` and `ChapterWorkflowEngine` are application-layer
orchestrators above the unchanged Page `WorkflowEngine`. Both depend on the
`ProjectRepository` port and `EventBus` interface only; they do not know a
local-file adapter, select an Agent, or modify a Page transition. `Project`
now persists typed `Chapter` boundaries, while each Page remains the sole owner
of its production state and artifacts.

`WorkflowCoordinator` is intentionally thin: it delegates Project to Chapter
to the existing Page engine and persists the returned Page context through the
mapping port. `PageNumberWorkflowScheduler` contains the initial ordering rule
(lowest non-approved page) and can be replaced through its protocol without
changing either Engine. Each hierarchy `run` invokes at most one Page workflow,
stops at `QualityChecked`, and requires existing explicit approval before the
next Page advances. `ProjectStarted`, `ProjectCompleted`, `ChapterStarted`, and
`ChapterCompleted` are persisted and published through the existing EventBus.

## Phase 15 batch-workflow architecture review

`BatchWorkflowEngine` is an outer application layer above persisted Project
work. `ExecutionPlanner` creates a deterministic ascending-page Queue with
explicit predecessor dependencies. The Batch engine loads and saves one Page
context around each Worker call; `WorkflowWorker` calls only the unchanged
`WorkflowEngine`. Batch code does not call Agents, select providers, or perform
Page state transitions.

Queue, progress, policy, logs, and Batch events are stored in
`Project.workflow["batches"]` through the existing `ProjectRepository` port.
Resume excludes completed Queue items. Retry requeues failed items only and
leaves later dependency-bound work pending until its predecessor completes.
Only `SequentialExecution` is executable. `ParallelExecution` and
`AutoExecution` are contracts only: there are no threads, processes, external
queues, Celery, RabbitMQ, Redis, or real parallel work in this phase.

## Phase 17 MCP-server architecture review

The local `mcp` package is an Application Layer delivery adapter. `McpServer`
receives stdio JSON-RPC requests, `ToolRegistry` validates a typed input model,
and `MangaApplicationService` delegates to `WorkflowEngine`,
`WorkflowCoordinator`, `ProjectLoader`, and the repository port. No MCP module
imports or calls an Agent, a `StateMachine`, image provider, or LLM provider.

Tool results are mapped to `McpToolResult`; Domain aggregates are serialized
inside DTO data rather than returned directly. `manga://` Resources are
read-only, Markdown Prompt assets stay under `prompts/`, and expected failures
are mapped to safe errors. `approve_page` explicitly requires `QualityChecked`
before invoking the existing approval command. The implementation is local
stdio only: HTTP, remote MCP, OAuth, API keys, JWT, and background transports
remain excluded.

## Phase 18 Web-UI architecture review

`web/` is an independent Next.js + TypeScript Presentation Layer. Its only
integration boundary is `web/lib/api/client.ts`, which calls a separately
compatible HTTP API with typed DTOs. No frontend module imports Python Domain models,
repositories, CLI code, MCP code, or Agents. Browser components render
API-supplied workflow state and available actions; they do not duplicate the
StateMachine or decide whether a transition is legal.

The Approval UI is shown from the API's `approvalRequired` field and submits an
explicit human identity through the REST client. Error boundaries, loading and
empty states, URL encoding, strict HTTP(S) API URL validation, semantic HTML,
and keyboard focus styling form the minimum safety and accessibility baseline.

## v2.2.0 final architecture audit

The current implementation preserves the inward dependency direction:

```text
Presentation (CLI / local MCP / Web UI) -> Application (Director / Workflow) -> Domain
                                              |                         ^
                                              v                         |
                                      Ports (EventBus / Repository) <- Infrastructure
```

- `domain/` imports neither workflow, delivery, provider, plugin, nor
  repository modules; the architecture test enforces this boundary.
- The Page `WorkflowEngine` depends on Domain contracts, `EventBus`, and an
  optional observer only. It does not import Agents, concrete repositories,
  CLI, MCP, Web UI, or provider implementations.
- Project/Chapter/Batch engines use the `ProjectRepository` protocol as a
  persistence port. Although the protocol is physically named under
  `repositories`, no workflow code selects a concrete persistence adapter.
- Plugin and SDK packages are outer extension boundaries. They are loaded by
  composition roots and cannot change `PageState`, skip a transition, or call
  Agents from Agents.
- The Web UI is an independent TypeScript presentation layer. The optional
  FastAPI adapter exposes observability DTOs only; it is not a workflow REST
  API or a Web UI backend. `manga_director.api` depends inward on DTO providers
  and never exposes Domain models.

No circular import failure or Core-to-Presentation dependency was found in the
import, architecture, and package-install release checks. The one-page,
forward-only StateMachine remains the source of truth for all workflow entry
points.
