"""Ordered orchestration for independently replaceable prompt stages."""

from __future__ import annotations

from typing import Any

from manga_director.domain.state_machine import PageState
from manga_director.prompting.builder import PromptBuilder
from manga_director.prompting.contracts import (
    PromptBuilderPort,
    PromptInput,
    PromptOptimizerPort,
    PromptRendererPort,
    PromptResult,
    PromptTemplateLoaderPort,
    PromptValidatorPort,
)
from manga_director.prompting.optimizer import PromptOptimizer
from manga_director.prompting.renderer import PromptRenderer
from manga_director.prompting.templates import PromptTemplateLoader
from manga_director.prompting.validator import PromptValidator
from manga_director.workflow import WorkflowContext


class PromptPipeline:
    """Controls Builder → Optimizer → Validator → Renderer for one page only."""

    def __init__(
        self,
        *,
        template_loader: PromptTemplateLoaderPort | None = None,
        builder: PromptBuilderPort | None = None,
        optimizer: PromptOptimizerPort | None = None,
        validator: PromptValidatorPort | None = None,
        renderer: PromptRendererPort | None = None,
        default_template: str = "image_prompt.md",
        optimizer_enabled: bool = True,
        validation_enabled: bool = True,
    ) -> None:
        self._template_loader = template_loader or PromptTemplateLoader()
        self._builder = builder or PromptBuilder()
        self._optimizer = optimizer or PromptOptimizer()
        self._validator = validator or PromptValidator()
        self._renderer = renderer or PromptRenderer()
        self._default_template = default_template
        self._optimizer_enabled = optimizer_enabled
        self._validation_enabled = validation_enabled

    def run(self, context: WorkflowContext) -> PromptResult:
        """Build, optionally optimize/validate, and render one page prompt in order."""
        template_name = str(context.metadata.get("prompt_template", self._default_template))
        template = self._template_loader.load(template_name)
        structured = self._builder.build(self._input_from_context(context))
        if self._optimizer_enabled:
            structured = self._optimizer.optimize(structured)
        warnings: list[str] = []
        if self._validation_enabled:
            warnings = self._validator.validate(structured, template).warnings
        result = self._renderer.render(structured, template)
        return result.model_copy(
            update={
                "warnings": warnings,
                "metadata": {
                    **result.metadata,
                    "optimizer_enabled": self._optimizer_enabled,
                    "validation_enabled": self._validation_enabled,
                },
            },
            deep=True,
        )

    @staticmethod
    def _input_from_context(context: WorkflowContext) -> PromptInput:
        page_design = PromptPipeline._artifact(context, PageState.DESIGNED)
        storyboard = PromptPipeline._artifact(context, PageState.STORYBOARDED)
        dialogue_artifact = context.artifacts.get("support:dialogue", {})
        dialogue_source = (
            dialogue_artifact.get("dialogue", []) if isinstance(dialogue_artifact, dict) else []
        )
        dialogue = [str(line) for line in dialogue_source]
        character = context.metadata.get("character", context.page.get("character", {}))
        if not isinstance(character, dict):
            character = {}
        if not character.get("name") and page_design.get("featured_character"):
            character = {**character, "name": page_design["featured_character"]}
        world = context.metadata.get("world", context.page.get("world", {}))
        if not isinstance(world, dict):
            world = {}
        page_number = context.page.get("page_number", context.page.get("page_id", ""))
        return PromptInput(
            page_number=str(page_number),
            page_design=page_design,
            storyboard=storyboard,
            dialogue=dialogue,
            character=character,
            world=world,
            metadata={"workflow_state": context.state.value},
        )

    @staticmethod
    def _artifact(context: WorkflowContext, state: PageState) -> dict[str, Any]:
        value = context.artifacts.get(state.value, {})
        return value if isinstance(value, dict) else {}
