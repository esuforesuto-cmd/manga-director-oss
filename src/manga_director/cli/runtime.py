from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, cast

from manga_director.adapters.factory import ImageGeneratorFactory
from manga_director.adapters.image_generator import ImageGenerator, ImageResult
from manga_director.adapters.llm_factory import LLMFactory
from manga_director.adapters.llm_provider import LLMProvider, LLMResult, PromptRequest
from manga_director.adapters.runtime import ImageBackendRuntime, LLMProviderRuntime
from manga_director.agents.registry import primary_agents, support_agents
from manga_director.cli.config import AppConfig
from manga_director.cli.logging import configure_logging
from manga_director.domain.exceptions import ImageGeneratorError, LLMProviderError
from manga_director.domain.state_machine import StateMachine
from manga_director.events import MemoryEventBus
from manga_director.plugins import (
    PluginManager,
    PluginRegistry,
    apply_agent_plugins,
    apply_image_generator_plugins,
    apply_llm_plugins,
)
from manga_director.prompting import PromptPipeline, PromptTemplateLoader
from manga_director.repositories import ProjectLoader
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow import (
    BatchWorkflowEngine,
    ChapterWorkflowEngine,
    PageNumberWorkflowScheduler,
    ProjectWorkflowEngine,
    WorkflowCoordinator,
    WorkflowEngine,
    WorkflowWorker,
)
from manga_director.workflow.contracts import WorkflowContext
from manga_director.workflow.durable_execution import LogicalOutputAssetQualityGatePort
from manga_director.workflow.localfile_durable_routing import build_localfile_durable_workflow
from manga_director.workflow.localfile_external_generated_application import (
    LocalFileExternalGenerationComposition,
    build_localfile_external_generation_composition,
)


@dataclass(frozen=True)
class CliRuntime:
    config: AppConfig
    engine: WorkflowEngine
    loader: ProjectLoader
    plugins: PluginManager
    coordinator: WorkflowCoordinator
    batch: BatchWorkflowEngine
    prompt_directory: Path | None
    providers: LLMProviderRuntime
    backends: ImageBackendRuntime
    localfile_external_generation: LocalFileExternalGenerationComposition | None = None


class _LazyImageGenerator:
    """Instantiate the configured image adapter only when a workflow generates an image."""

    def __init__(self, provider: str) -> None:
        self._provider = provider
        self._delegate: ImageGenerator | None = None
        self._lock = Lock()

    def generate(self, prompt: str) -> ImageResult:
        if self._delegate is None:
            with self._lock:
                if self._delegate is None:
                    self._delegate = ImageGeneratorFactory.create(self._provider)
        return self._delegate.generate(prompt)


class _LazyLLMProvider:
    """Instantiate the configured LLM adapter only when an Agent requests it."""

    def __init__(self, provider: str) -> None:
        self._provider = provider
        self._delegate: LLMProvider | None = None
        self._lock = Lock()

    def generate(self, request: PromptRequest) -> LLMResult:
        if self._delegate is None:
            with self._lock:
                if self._delegate is None:
                    self._delegate = LLMFactory.create(self._provider)
        return self._delegate.generate(request)


class _LazyLocalFileExternalGenerationComposition:
    """Resolve the private LocalFile durability graph only when Quality needs it."""

    def __init__(
        self,
        repository: LocalFileRepository,
        state_machine: StateMachine,
        event_bus: MemoryEventBus,
    ) -> None:
        self._repository = repository
        self._state_machine = state_machine
        self._event_bus = event_bus
        self._delegate: LocalFileExternalGenerationComposition | None = None
        self._lock = Lock()

    @property
    def quality_gate(self) -> LogicalOutputAssetQualityGatePort:
        return self

    def require_applied(self, context: WorkflowContext) -> str | None:
        return self._resolve().quality_gate.require_applied(context)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._resolve(), name)

    def _resolve(self) -> LocalFileExternalGenerationComposition:
        if self._delegate is None:
            with self._lock:
                if self._delegate is None:
                    self._delegate = build_localfile_external_generation_composition(
                        self._repository, self._state_machine, self._event_bus
                    )
        return self._delegate


def build_runtime(config: AppConfig, config_directory: Path) -> CliRuntime:
    """Composition root. CLI command handlers receive only this Engine-facing runtime."""
    logger = configure_logging(config.log_level)
    plugin_directory = config.plugin_directory
    if not plugin_directory.is_absolute():
        plugin_directory = config_directory / plugin_directory
    plugins = PluginManager(plugin_directory, PluginRegistry())
    plugins.load_enabled()
    apply_image_generator_plugins(plugins.registry)
    apply_llm_plugins(plugins.registry)
    _validate_image_generator(config.default_image_generator)
    _validate_llm_provider(config.default_llm_provider)
    generator = _LazyImageGenerator(config.default_image_generator)
    llm_provider = _LazyLLMProvider(config.default_llm_provider)
    prompt_directory = config.prompt_directory
    if prompt_directory is not None and not prompt_directory.is_absolute():
        prompt_directory = config_directory / prompt_directory
    prompt_pipeline = PromptPipeline(
        template_loader=PromptTemplateLoader(prompt_directory),
        default_template=config.default_prompt_template,
        optimizer_enabled=config.optimizer_enabled,
        validation_enabled=config.validation_enabled,
    )
    primary, support = apply_agent_plugins(
        plugins.registry,
        primary_agents(generator, prompt_directory, llm_provider, prompt_pipeline),
        support_agents(llm_provider, prompt_directory),
    )
    event_bus = MemoryEventBus()
    state_machine = StateMachine()
    engine = WorkflowEngine(
        state_machine=state_machine,
        event_bus=event_bus,
        agents=primary,
        support_agents=support,
    )
    loader = ProjectLoader.from_settings(
        config.repository.driver,
        config.repository.root,
        config.repository.format,
        config_directory,
        config.database_provider,
        config.database_url,
    )
    project_engine = ProjectWorkflowEngine(loader.repository, event_bus)
    coordinator: WorkflowCoordinator
    batch: BatchWorkflowEngine
    localfile_external_generation: _LazyLocalFileExternalGenerationComposition | None = None
    if isinstance(loader.repository, LocalFileRepository):
        localfile_external_generation = _LazyLocalFileExternalGenerationComposition(
            loader.repository, state_machine, event_bus
        )
        coordinator, batch = build_localfile_durable_workflow(
            loader.repository,
            engine,
            event_bus,
            logical_output_asset_quality_gate=localfile_external_generation.quality_gate,
        )
    else:
        coordinator = WorkflowCoordinator(
            project_engine,
            ChapterWorkflowEngine(loader.repository, event_bus, PageNumberWorkflowScheduler()),
            engine,
            loader,
        )
        batch = BatchWorkflowEngine(
            loader.repository,
            loader,
            WorkflowWorker(engine),
            event_bus,
            project_engine=project_engine,
        )
    logger.debug("CLI runtime initialized")
    return CliRuntime(
        config=config,
        engine=engine,
        plugins=plugins,
        loader=loader,
        coordinator=coordinator,
        batch=batch,
        prompt_directory=prompt_directory,
        providers=LLMProviderRuntime(),
        backends=ImageBackendRuntime(),
        localfile_external_generation=cast(
            LocalFileExternalGenerationComposition | None, localfile_external_generation
        ),
    )


def _validate_image_generator(provider: str) -> None:
    if provider.strip().lower() not in ImageGeneratorFactory.available():
        raise ImageGeneratorError(f"Unsupported image generator: {provider}")


def _validate_llm_provider(provider: str) -> None:
    if provider.strip().lower() not in LLMFactory.available():
        raise LLMProviderError(f"Unsupported LLM provider: {provider}")
