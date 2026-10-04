from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from manga_director.adapters import LLMFactory, LLMResult, PromptRequest
from manga_director.adapters.llm_factory import LLMBuilder
from manga_director.adapters.llm_provider import LLMProvider
from manga_director.cli.config import AppConfig
from manga_director.cli.runtime import build_runtime
from manga_director.domain.exceptions import LLMProviderError
from manga_director.workflow import WorkflowContext


@dataclass
class FixtureLLM:
    requests: list[PromptRequest] = field(default_factory=list)

    def generate(self, request: PromptRequest) -> LLMResult:
        self.requests.append(request)
        return LLMResult(
            success=True,
            content="fixture response",
            usage={"input_tokens": 1, "output_tokens": 1},
            provider="fixture",
            elapsed_time=0.0,
            finish_reason="stop",
            metadata={},
            messages=["fixture"],
        )


def test_llm_factory_exposes_builtin_provider_registry() -> None:
    expected = {"anthropic", "gemini", "litellm", "mock", "ollama", "openai", "openrouter"}
    assert expected.issubset(LLMFactory.available())


def test_llm_factory_registers_custom_builders_without_provider_branches() -> None:
    LLMFactory.register("fixture", FixtureLLM)

    provider = LLMFactory.create("fixture")
    assert isinstance(provider, FixtureLLM)
    assert provider.generate(PromptRequest(user_prompt="test")).provider == "fixture"


def test_llm_factory_rejects_unknown_provider() -> None:
    with pytest.raises(LLMProviderError, match="Unsupported LLM provider"):
        LLMFactory.create("unknown")


def test_mock_llm_returns_a_complete_deterministic_result() -> None:
    request = PromptRequest(system_prompt="system", user_prompt="user", metadata={"page": "001"})
    result = LLMFactory.create("mock").generate(request)

    assert result.success is True
    assert result.provider == "mock"
    assert result.content == "Mock LLM response."
    assert result.response.content == result.content
    assert result.metadata["request_metadata"] == {"page": "001"}


def test_stub_providers_do_not_make_real_api_requests() -> None:
    result = LLMFactory.create("openai").generate(PromptRequest(user_prompt="test"))

    assert result.success is False
    assert result.finish_reason == "not_implemented"
    assert "stub" in result.messages[0]


def test_llm_builder_alias_satisfies_the_provider_protocol() -> None:
    builder: LLMBuilder = FixtureLLM
    assert isinstance(builder(), LLMProvider)


def test_runtime_selects_configured_llm_through_the_factory(tmp_path: Path) -> None:
    runtime = build_runtime(AppConfig(default_llm_provider="mock"), tmp_path)
    result = runtime.engine.execute(WorkflowContext())

    assert result.current_state.value == "Designed"
    assert "LLM assistance completed by mock." in result.logs
