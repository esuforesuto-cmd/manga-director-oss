from __future__ import annotations

from pathlib import Path

import pytest

from manga_director.agents import PromptAgent
from manga_director.domain.exceptions import ValidationError
from manga_director.domain.state_machine import PageState
from manga_director.prompting import (
    PromptBuilder,
    PromptInput,
    PromptOptimizer,
    PromptPipeline,
    PromptRenderer,
    PromptResult,
    PromptTemplate,
    PromptTemplateLoader,
    PromptValidation,
    PromptValidator,
    StructuredPrompt,
)
from manga_director.workflow import WorkflowContext


def _input() -> PromptInput:
    return PromptInput(
        page_number="1",
        page_design={
            "page_type": "drama",
            "purpose": "Reveal the clue",
            "featured_character": "Aki",
        },
        storyboard={"panels": [{"number": 1, "action": "turn"}]},
        dialogue=["Look."],
        character={"name": "Aki"},
        world={"location": "library"},
    )


def _template() -> PromptTemplate:
    return PromptTemplate(
        name="fixture.md",
        content="{page_number}|{page_type}|{purpose}|{panels}|{dialogue}|{character}|{world}",
        source="test",
        content_hash="fixture",
    )


def test_builder_creates_a_structured_prompt_from_all_source_artifacts() -> None:
    prompt = PromptBuilder().build(_input())

    assert prompt.page_number == "1"
    assert prompt.sections["page_type"] == "drama"
    assert prompt.sections["purpose"] == "Reveal the clue"
    assert prompt.character["name"] == "Aki"
    assert prompt.panels[0]["action"] == "turn"


def test_optimizer_removes_redundancy_and_provider_directives() -> None:
    prompt = StructuredPrompt(
        page_number="1",
        panels=[{"number": 1}],
        character={"name": "Aki"},
        sections={
            "page_type": "manga\nprovider: example\nmanga",
            "purpose": "Reveal clue\nReveal clue",
            "panels": "[]",
        },
    )

    optimized = PromptOptimizer().optimize(prompt)

    assert optimized.sections["page_type"] == "manga"
    assert optimized.sections["purpose"] == "Reveal clue"


def test_optimizer_is_deterministic_and_does_not_mutate_source_prompt() -> None:
    prompt = StructuredPrompt(
        page_number="1",
        page_design={"purpose": "Reveal clue"},
        panels=[{"number": 1, "action": "turn"}],
        dialogue=["Look.", "Look.", "Wait."],
        character={"name": "Aki"},
        sections={
            "page_type": "manga",
            "purpose": "Reveal clue\nReveal clue\nmodel: test\nWait.",
            "panels": '[{"number": 1}]',
        },
    )
    before = prompt.model_dump()

    optimized = PromptOptimizer().optimize(prompt)

    assert optimized.dialogue == ["Look.", "Wait."]
    assert optimized.sections["purpose"] == "Reveal clue\nWait."
    assert optimized.page_design == prompt.page_design
    assert optimized.panels == prompt.panels
    assert prompt.model_dump() == before
    assert PromptOptimizer().optimize(prompt) == optimized


def test_validator_rejects_missing_fields_forbidden_words_and_template_mismatches() -> None:
    prompt = StructuredPrompt(
        page_number="",
        panels=[],
        character={},
        sections={"page_type": "manga", "purpose": "forbidden draft", "panels": "[]"},
    )
    validator = PromptValidator(forbidden_words=("forbidden",))

    with pytest.raises(ValidationError, match="page number"):
        validator.validate(prompt, _template())


def test_renderer_renders_markdown_and_reports_token_count() -> None:
    structured = PromptBuilder().build(_input())
    result = PromptRenderer().render(structured, _template())

    assert result.success is True
    assert result.prompt.startswith("1|drama|Reveal the clue")
    assert result.tokens > 0
    assert result.metadata["template"] == "fixture.md"


def test_pipeline_controls_stage_order_and_returns_rendered_result() -> None:
    calls: list[str] = []

    class Builder:
        def build(self, source: PromptInput) -> StructuredPrompt:
            calls.append("build")
            return PromptBuilder().build(source)

    class Optimizer:
        def optimize(self, prompt: StructuredPrompt) -> StructuredPrompt:
            calls.append("optimize")
            return prompt

    class Validator:
        def validate(self, prompt: StructuredPrompt, template: PromptTemplate) -> PromptValidation:
            calls.append("validate")
            return PromptValidator().validate(prompt, template)

    class Renderer:
        def render(self, prompt: StructuredPrompt, template: PromptTemplate) -> PromptResult:
            calls.append("render")
            return PromptRenderer().render(prompt, template)

    loader = PromptTemplateLoader()
    loader.register(_template())
    context = WorkflowContext(
        page={"page_id": "1"},
        state=PageState.STORYBOARDED,
        artifacts={
            "Designed": _input().page_design,
            "Storyboarded": _input().storyboard,
            "support:dialogue": {"dialogue": _input().dialogue},
        },
        metadata={
            "character": _input().character,
            "world": _input().world,
            "prompt_template": "fixture.md",
        },
    )
    pipeline = PromptPipeline(
        template_loader=loader,
        builder=Builder(),
        optimizer=Optimizer(),
        validator=Validator(),
        renderer=Renderer(),
    )

    result = pipeline.run(context)

    assert calls == ["build", "optimize", "validate", "render"]
    assert result.success is True


def test_pipeline_rejects_missing_storyboard_without_mutating_workflow_context() -> None:
    context = WorkflowContext(
        page={"page_id": "1"},
        state=PageState.DESIGNED,
        artifacts={"Designed": _input().page_design},
        metadata={"character": _input().character},
    )
    before = context.model_dump()

    with pytest.raises(ValidationError, match="storyboard panels are required"):
        PromptPipeline().run(context)

    assert context.model_dump() == before


def test_template_loader_uses_custom_markdown_and_registered_plugin_templates(
    tmp_path: Path,
) -> None:
    (tmp_path / "custom.md").write_text("{page_type}|{purpose}|{panels}", encoding="utf-8")
    loader = PromptTemplateLoader(tmp_path)

    assert loader.load("custom.md").source == str(tmp_path / "custom.md")
    loader.register(_template())
    assert loader.load("fixture.md") == _template()


def test_template_loader_rejects_non_markdown_or_traversal_names() -> None:
    loader = PromptTemplateLoader()

    with pytest.raises(ValidationError, match="Markdown"):
        loader.load("../secret.txt")


def test_prompt_agent_calls_only_its_pipeline() -> None:
    calls: list[WorkflowContext] = []

    class Pipeline:
        def run(self, context: WorkflowContext) -> PromptResult:
            calls.append(context)
            return PromptResult(
                success=True,
                prompt="# pipeline prompt",
                tokens=2,
                warnings=[],
                metadata={},
                messages=["pipeline complete"],
            )

    context = WorkflowContext()
    result = PromptAgent(Pipeline()).execute(context)  # type: ignore[arg-type]

    assert calls == [context]
    assert result.payload["prompt_markdown"] == "# pipeline prompt"
    assert result.messages == ["pipeline complete"]
