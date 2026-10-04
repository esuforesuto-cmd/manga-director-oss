from __future__ import annotations

from pathlib import Path
from typing import Any

from manga_director.adapters.image_generator import ImageGenerator
from manga_director.adapters.llm_provider import LLMProvider
from manga_director.agents.base import BaseAgent
from manga_director.agents.llm_support import LLMAssistance
from manga_director.domain.state_machine import PageState
from manga_director.prompting import PromptPipeline
from manga_director.workflow.contracts import AgentResult, WorkflowContext


def _artifact(context: WorkflowContext, state: PageState) -> dict[str, Any]:
    value = context.artifacts.get(state.value, {})
    return value if isinstance(value, dict) else {}


class PageDesignAgent(LLMAssistance, BaseAgent):
    target_state = PageState.DESIGNED

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        prompt_directory: Path | None = None,
    ) -> None:
        super().__init__(llm_provider, prompt_directory)

    def execute(self, context: WorkflowContext) -> AgentResult:
        source = context.metadata.get("page_design", {})
        panel_count = int(source.get("panel_count", 4))
        panel_roles = source.get(
            "panel_roles",
            ["setup", "escalation", "big moment", "hook"][:panel_count],
        )
        payload = {
            "page_type": source.get("page_type", "story"),
            "purpose": source.get("purpose", "Advance one clear story beat."),
            "reader_emotion": source.get("reader_emotion", "anticipation"),
            "featured_character": source.get("featured_character", "protagonist"),
            "big_moment": source.get("big_moment", "A decisive reveal."),
            "hook": source.get("hook", "A question that compels the next page."),
            "panel_count": panel_count,
            "panel_roles": panel_roles,
        }
        return self.result(
            payload=payload,
            messages=["Page design created.", *self.llm_messages(context, "PageDesignAgent")],
        )


class EditorAgent(LLMAssistance, BaseAgent):
    target_state = PageState.REVIEWED

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        prompt_directory: Path | None = None,
    ) -> None:
        super().__init__(llm_provider, prompt_directory)

    def execute(self, context: WorkflowContext) -> AgentResult:
        design = _artifact(context, PageState.DESIGNED)
        panel_count = int(design.get("panel_count", 0))
        purpose = str(design.get("purpose", ""))
        checks = {
            "single_purpose": bool(purpose) and ";" not in purpose,
            "information_amount": 1 <= panel_count <= 7,
            "character": bool(design.get("featured_character")),
            "direction": bool(design.get("big_moment")),
            "hook": bool(design.get("hook")),
        }
        improvements = [
            f"Improve {name.replace('_', ' ')}." for name, passed in checks.items() if not passed
        ]
        return self.result(
            payload={"checks": checks, "improvements": improvements},
            messages=["Editorial review completed.", *self.llm_messages(context, "EditorAgent")],
        )


class StoryboardAgent(LLMAssistance, BaseAgent):
    target_state = PageState.STORYBOARDED

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        prompt_directory: Path | None = None,
    ) -> None:
        super().__init__(llm_provider, prompt_directory)

    def execute(self, context: WorkflowContext) -> AgentResult:
        design = _artifact(context, PageState.DESIGNED)
        roles = design.get("panel_roles", ["setup"])
        panels = [
            {
                "number": index,
                "role": role,
                "composition": "clear focal composition",
                "camera": "medium shot",
                "characters": [design.get("featured_character", "protagonist")],
                "background": "story-relevant setting",
                "expression": "focused",
                "action": "advance the page purpose",
                "dialogue": [],
                "sound_effect": "",
                "balloon_position": "upper right",
            }
            for index, role in enumerate(roles, start=1)
        ]
        return self.result(
            payload={"panels": panels},
            messages=["Storyboard created.", *self.llm_messages(context, "StoryboardAgent")],
        )


class DialogueAgent(LLMAssistance, BaseAgent):
    """Refines dialogue supplied in an existing storyboard without changing workflow state."""

    target_state = PageState.STORYBOARDED

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        prompt_directory: Path | None = None,
    ) -> None:
        super().__init__(llm_provider, prompt_directory)

    def execute(self, context: WorkflowContext) -> AgentResult:
        storyboard = _artifact(context, PageState.STORYBOARDED)
        source_lines = context.metadata.get("dialogue", storyboard.get("dialogue", []))
        refined = [" ".join(str(line).split())[:48] for line in source_lines]
        return self.result(
            payload={"dialogue": refined},
            messages=[
                "Dialogue refined for concise, readable balloons.",
                *self.llm_messages(context, "DialogueAgent"),
            ],
        )


class PromptAgent(BaseAgent):
    target_state = PageState.PROMPT_BUILT

    def __init__(self, pipeline: PromptPipeline | None = None) -> None:
        self._pipeline = pipeline or PromptPipeline()

    def execute(self, context: WorkflowContext) -> AgentResult:
        result = self._pipeline.run(context)
        return self.result(
            payload={
                "prompt_markdown": result.prompt,
                "tokens": result.tokens,
                "warnings": result.warnings,
                "metadata": result.metadata,
            },
            messages=result.messages,
        )


class ImageAgent(BaseAgent):
    target_state = PageState.GENERATED

    def __init__(self, generator: ImageGenerator) -> None:
        self._generator = generator

    def execute(self, context: WorkflowContext) -> AgentResult:
        prompt = _artifact(context, PageState.PROMPT_BUILT).get("prompt_markdown")
        if not isinstance(prompt, str) or not prompt:
            raise ValueError("ImageAgent requires a PromptBuilt prompt artifact.")
        image = self._generator.generate(prompt)
        return AgentResult(
            success=image.success,
            state=self.target_state,
            payload={
                "image_path": image.image_path,
                "metadata": image.metadata,
                "provider": image.provider,
                "elapsed_time": image.elapsed_time,
            },
            events=[],
            messages=image.messages,
        )


class QualityAgent(LLMAssistance, BaseAgent):
    target_state = PageState.QUALITY_CHECKED
    _criteria = (
        "readability",
        "composition",
        "direction",
        "background",
        "character_fidelity",
        "dialogue",
        "eye_flow",
        "tempo",
        "page_purpose",
        "hook",
    )

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        prompt_directory: Path | None = None,
    ) -> None:
        super().__init__(llm_provider, prompt_directory)

    def execute(self, context: WorkflowContext) -> AgentResult:
        supplied_scores = context.metadata.get("quality_scores", {})
        scores = {criterion: int(supplied_scores.get(criterion, 5)) for criterion in self._criteria}
        invalid = [name for name, score in scores.items() if not 0 <= score <= 5]
        if invalid:
            raise ValueError(f"Quality scores must be between 0 and 5: {', '.join(invalid)}")
        failed = [name for name, score in scores.items() if score < 4]
        return self.result(
            payload={"scores": scores, "passed": not failed, "failed_criteria": failed},
            messages=[
                "Quality review passed." if not failed else "Quality review failed.",
                *self.llm_messages(context, "QualityAgent"),
            ],
        )


class ContinuityAgent(BaseAgent):
    """Reports supplied previous/current page differences without mutating either page."""

    target_state = PageState.DESIGNED
    _criteria = ("character", "costume", "props", "time", "location", "emotion")

    def execute(self, context: WorkflowContext) -> AgentResult:
        previous = context.metadata.get("previous_page", {})
        current = context.metadata.get("current_page", context.page)
        warnings = [
            f"Continuity mismatch: {criterion}."
            for criterion in self._criteria
            if previous.get(criterion) is not None
            and current.get(criterion) is not None
            and previous[criterion] != current[criterion]
        ]
        return self.result(
            payload={"warnings": warnings, "consistent": not warnings},
            messages=["Continuity check completed."],
        )


class ApprovalAgent(BaseAgent):
    """Records human approval evidence; the WorkflowEngine performs the state transition."""

    target_state = PageState.APPROVED

    def execute(self, context: WorkflowContext) -> AgentResult:
        approved_by = context.metadata.get("approved_by")
        if not isinstance(approved_by, str) or not approved_by.strip():
            raise ValueError("ApprovalAgent requires human metadata 'approved_by'.")
        return self.result(
            payload={"approved_by": approved_by.strip()},
            messages=["Human approval recorded."],
        )
