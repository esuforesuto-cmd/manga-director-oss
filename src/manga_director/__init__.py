"""Public API for manga-director."""

from manga_director._version import __version__
from manga_director.adapters.image_generator import ImageGenerator, ImageResult
from manga_director.adapters.llm_provider import (
    LLMProvider,
    LLMResult,
    PromptRequest,
    PromptResponse,
)
from manga_director.director import Director
from manga_director.domain.exceptions import (
    CLIError,
    ConfigurationError,
    ImageGeneratorError,
    MangaDirectorError,
    RepositoryError,
    StateTransitionError,
    ValidationError,
    WorkflowError,
)
from manga_director.domain.project import Page, Project
from manga_director.repositories.protocols import ProjectRepository as Repository
from manga_director.workflow import WorkflowContext, WorkflowEngine

__all__ = [
    "CLIError",
    "ConfigurationError",
    "Director",
    "ImageGenerator",
    "ImageGeneratorError",
    "ImageResult",
    "LLMProvider",
    "LLMResult",
    "MangaDirectorError",
    "Page",
    "Project",
    "PromptRequest",
    "PromptResponse",
    "Repository",
    "RepositoryError",
    "StateTransitionError",
    "ValidationError",
    "WorkflowContext",
    "WorkflowEngine",
    "WorkflowError",
    "__version__",
]
