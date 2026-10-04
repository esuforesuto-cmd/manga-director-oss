from __future__ import annotations

from pathlib import Path

from manga_director.adapters.factory import ImageGeneratorFactory
from manga_director.adapters.llm_factory import LLMFactory
from manga_director.agents.registry import primary_agents, support_agents
from manga_director.domain.state_machine import StateMachine
from manga_director.events import MemoryEventBus
from manga_director.prompting import PromptPipeline, PromptTemplateLoader
from manga_director.workflow import WorkflowContext, WorkflowEngine, WorkflowResult, WorkflowStatus


class Director:
    """Small public facade that coordinates calls to a configured WorkflowEngine."""

    def __init__(self, engine: WorkflowEngine) -> None:
        self._engine = engine

    @classmethod
    def default(
        cls,
        *,
        image_generator: str = "mock",
        llm_provider: str = "mock",
        prompt_directory: Path | None = None,
    ) -> Director:
        """Build a local, in-memory workflow director using a registered image provider."""
        generator = ImageGeneratorFactory.create(image_generator)
        llm = LLMFactory.create(llm_provider)
        prompt_pipeline = PromptPipeline(template_loader=PromptTemplateLoader(prompt_directory))
        return cls(
            WorkflowEngine(
                state_machine=StateMachine(),
                event_bus=MemoryEventBus(),
                agents=primary_agents(generator, prompt_directory, llm, prompt_pipeline),
                support_agents=support_agents(llm, prompt_directory),
            )
        )

    def execute(self, context: WorkflowContext, command: str) -> WorkflowResult:
        return self._engine.execute_command(context, command)

    def run(self, context: WorkflowContext) -> list[WorkflowResult]:
        return self._engine.run(context)

    def status(self, context: WorkflowContext) -> WorkflowStatus:
        return self._engine.status(context)
