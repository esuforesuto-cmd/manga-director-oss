from pathlib import Path

from manga_director.adapters.factory import ImageGeneratorFactory
from manga_director.adapters.image_generator import ImageResult
from manga_director.adapters.mock_image_generator import MockImageGenerator
from manga_director.agents import ImageAgent
from manga_director.cli.config import AppConfig
from manga_director.cli.runtime import build_runtime
from manga_director.domain.state_machine import PageState
from manga_director.workflow import WorkflowContext


def test_factory_exposes_registered_builtin_providers() -> None:
    assert {"comfyui", "mock", "openai"}.issubset(ImageGeneratorFactory.available())


def test_factory_registers_and_creates_a_custom_provider() -> None:
    class FixtureGenerator:
        def generate(self, prompt: str) -> ImageResult:
            return ImageResult(
                success=True,
                image_path="fixture://page.png",
                metadata={},
                provider="fixture",
                elapsed_time=0.0,
                messages=[],
            )

    ImageGeneratorFactory.register("fixture", FixtureGenerator)

    assert ImageGeneratorFactory.create("fixture").generate("prompt").provider == "fixture"


def test_mock_generator_returns_a_fixed_successful_image_result() -> None:
    result = MockImageGenerator().generate("a prompt")

    assert result.success is True
    assert result.image_path == "mock://generated-page.png"
    assert result.provider == "mock"
    assert result.elapsed_time == 0.0


def test_image_agent_delegates_only_to_the_generator_contract() -> None:
    result = ImageAgent(MockImageGenerator()).execute(
        WorkflowContext(artifacts={"PromptBuilt": {"prompt_markdown": "a prompt"}})
    )

    assert result.success is True
    assert result.state == PageState.GENERATED
    assert result.payload["provider"] == "mock"
    assert result.payload["image_path"] == "mock://generated-page.png"


def test_runtime_selects_configured_generator_via_factory(tmp_path: Path) -> None:
    runtime = build_runtime(AppConfig(default_image_generator="mock"), tmp_path)
    result = runtime.engine.execute(
        WorkflowContext(
            state=PageState.PROMPT_BUILT,
            artifacts={"PromptBuilt": {"prompt_markdown": "a prompt"}},
        )
    )

    assert result.current_state == PageState.GENERATED
    assert result.context.artifacts["Generated"]["provider"] == "mock"
