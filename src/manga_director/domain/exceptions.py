"""Stable exception hierarchy for library and CLI consumers."""


class MangaDirectorError(Exception):
    """Base exception for all expected manga-director failures."""


class WorkflowError(MangaDirectorError):
    """Raised when a workflow operation cannot be completed."""


class StateTransitionError(WorkflowError):
    """Raised when a requested state transition is not legal."""


class InvalidPageTransition(StateTransitionError):
    """Backward-compatible name for an invalid state transition."""


class AgentExecutionError(WorkflowError):
    """Raised when an agent cannot produce a successful result."""


class AgentNotAvailableError(WorkflowError):
    """Raised when no agent is registered for a requested workflow operation."""


class RepositoryError(MangaDirectorError):
    """Raised when project persistence or retrieval fails."""


class ProjectNotFoundError(RepositoryError):
    """Raised when a requested project or page does not exist."""


class ProjectAlreadyExistsError(RepositoryError):
    """Raised when creation would overwrite an existing project."""


class ValidationError(MangaDirectorError):
    """Raised when a domain object does not satisfy persistence invariants."""


class ConfigurationError(MangaDirectorError):
    """Raised when application configuration cannot be loaded or interpreted."""


class ImageGeneratorError(MangaDirectorError):
    """Raised when an image-generator provider cannot be resolved or executed."""


class LLMProviderError(MangaDirectorError):
    """Raised when an LLM provider cannot be resolved or executed."""


class CLIError(MangaDirectorError):
    """Raised for command-line delivery errors that have no lower-level cause."""


class PluginError(MangaDirectorError):
    """Raised when plugin discovery, loading, or registration fails."""


class PluginManifestError(PluginError):
    """Raised when a plugin manifest is missing or invalid."""


class PluginDependencyError(PluginError):
    """Raised when plugin dependencies are missing, disabled, or cyclic."""


class PluginRegistrationError(PluginError):
    """Raised when a plugin contribution cannot be registered safely."""


class PluginLifecycleError(PluginError):
    """Raised when a plugin cannot be initialized, registered, or stopped."""
