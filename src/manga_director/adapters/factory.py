from __future__ import annotations

from collections.abc import Callable
from typing import Any

from manga_director.adapters.comfyui_image_generator import ComfyUIImageGenerator
from manga_director.adapters.image_generator import ImageGenerator
from manga_director.adapters.mock_image_generator import MockImageGenerator
from manga_director.adapters.openai_image_generator import OpenAIImageGenerator
from manga_director.adapters.runtime_models import AdapterMetadata
from manga_director.domain.exceptions import ConfigurationError, ImageGeneratorError

GeneratorBuilder = Callable[..., ImageGenerator]


class ImageGeneratorFactory:
    """Registry-backed provider factory with no provider-specific branching."""

    _registry: dict[str, GeneratorBuilder] = {}
    _metadata: dict[str, AdapterMetadata] = {}

    @classmethod
    def register(
        cls, provider: str, builder: GeneratorBuilder, metadata: AdapterMetadata | None = None
    ) -> None:
        normalized = provider.strip().lower()
        if not normalized:
            raise ConfigurationError("Image generator provider name is required.")
        cls._registry[normalized] = builder
        cls._metadata[normalized] = metadata or AdapterMetadata(
            name=normalized, display_name=normalized
        )

    @classmethod
    def create(cls, provider: str, **options: Any) -> ImageGenerator:
        normalized = provider.strip().lower()
        try:
            builder = cls._registry[normalized]
        except KeyError as exc:
            raise ImageGeneratorError(f"Unsupported image generator: {provider}") from exc
        return builder(**options)

    @classmethod
    def available(cls) -> list[str]:
        return sorted(cls._registry)

    @classmethod
    def metadata(cls) -> list[AdapterMetadata]:
        """Return registered backend metadata in deterministic priority order."""

        return sorted(cls._metadata.values(), key=lambda item: (item.priority, item.name))

    @classmethod
    def resolve(cls, backend_or_alias: str) -> str:
        """Resolve a backend name, model name, or preset alias without creating it."""

        normalized = backend_or_alias.strip().lower()
        matches = [
            metadata
            for metadata in cls.metadata()
            if normalized == metadata.name
            or normalized in {alias.lower() for alias in metadata.aliases}
            or normalized in {model.lower() for model in metadata.models}
            or normalized in {preset.lower() for preset in metadata.presets}
        ]
        if not matches:
            raise ImageGeneratorError(f"Unsupported image generator or alias: {backend_or_alias}")
        return matches[0].name


ImageGeneratorFactory.register(
    "mock",
    MockImageGenerator,
    AdapterMetadata(
        name="mock",
        display_name="Mock Image Generator",
        priority=0,
        capabilities=("image", "deterministic"),
        models=("mock-image",),
        aliases={"default": "mock-image", "offline": "mock-image"},
        presets={"test": {"model": "mock-image"}},
    ),
)
ImageGeneratorFactory.register(
    "openai",
    OpenAIImageGenerator,
    AdapterMetadata(name="openai", display_name="OpenAI Image", capabilities=("image",)),
)
ImageGeneratorFactory.register(
    "comfyui",
    ComfyUIImageGenerator,
    AdapterMetadata(
        name="comfyui",
        display_name="ComfyUI",
        capabilities=("image", "workflow"),
        workflow_metadata={"format": "workflow-json", "execution": "external"},
    ),
)
