"""Markdown-backed MCP prompt definitions without executable prompt code."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from manga_director.domain.exceptions import ValidationError
from manga_director.mcp.contracts import McpPrompt


class McpPromptLoader:
    """Load named MCP prompt assets from prompts/ without embedding prompt text in code."""

    _prompts = {
        "design_manga_page": ("mcp_design_manga_page.md", "Plan one manga page."),
        "review_manga_page": ("mcp_review_manga_page.md", "Review one designed manga page."),
        "create_manga_storyboard": (
            "mcp_create_manga_storyboard.md",
            "Create a storyboard for one reviewed page.",
        ),
        "optimize_manga_dialogue": (
            "mcp_optimize_manga_dialogue.md",
            "Improve dialogue for one storyboarded page.",
        ),
        "build_manga_image_prompt": (
            "mcp_build_manga_image_prompt.md",
            "Build an image prompt for one storyboarded page.",
        ),
        "review_manga_quality": (
            "mcp_review_manga_quality.md",
            "Review quality for one generated page.",
        ),
    }

    def __init__(self, prompt_directory: Path | None = None) -> None:
        self._prompt_directory = prompt_directory

    def list(self) -> list[McpPrompt]:
        return [
            McpPrompt(name=name, description=description, arguments=["project_id", "page_number"])
            for name, (_, description) in self._prompts.items()
        ]

    def get(self, name: str, arguments: dict[str, str] | None = None) -> str:
        try:
            filename, _ = self._prompts[name]
        except KeyError as exc:
            raise ValidationError(f"Unknown MCP prompt '{name}'.") from exc
        template = self._read(filename)
        for key, value in (arguments or {}).items():
            template = template.replace("{{" + key + "}}", value)
        return template

    def _read(self, filename: str) -> str:
        if self._prompt_directory is not None:
            candidate = self._prompt_directory / filename
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")
        return files("manga_director.prompts").joinpath(filename).read_text(encoding="utf-8")
