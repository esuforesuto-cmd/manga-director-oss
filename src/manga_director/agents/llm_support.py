"""Provider-neutral LLM assistance shared by stateless workflow agents."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path

from manga_director.adapters.llm_provider import LLMProvider, PromptRequest
from manga_director.workflow.contracts import WorkflowContext


class LLMAssistance:
    """Renders Markdown prompt templates and delegates only to an LLMProvider."""

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        prompt_directory: Path | None = None,
    ) -> None:
        self._llm_provider = llm_provider
        self._llm_prompt_directory = prompt_directory

    def llm_messages(self, context: WorkflowContext, agent_name: str) -> list[str]:
        """Run optional advisory assistance without affecting workflow legality."""
        if self._llm_provider is None:
            return []
        context_json = json.dumps(
            context.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
        )
        request = PromptRequest(
            user_prompt=self._llm_template().format(
                agent_name=agent_name,
                context_json=context_json,
            ),
            metadata={"agent": agent_name, "page_state": context.state.value},
        )
        result = self._llm_provider.generate(request)
        if result.success:
            return [f"LLM assistance completed by {result.provider}."]
        return [f"LLM assistance unavailable: {'; '.join(result.messages)}"]

    def _llm_template(self) -> str:
        if self._llm_prompt_directory is not None:
            candidate = self._llm_prompt_directory / "agent_assist.md"
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")
        template = files("manga_director.prompts").joinpath("agent_assist.md")
        return template.read_text(encoding="utf-8")
