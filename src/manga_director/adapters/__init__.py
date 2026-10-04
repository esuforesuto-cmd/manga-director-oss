"""External-system ports and provider factories used by agents."""

from manga_director.adapters.factory import ImageGeneratorFactory
from manga_director.adapters.image_generator import ImageGenerator, ImageResult
from manga_director.adapters.lifecycle import (
    AdapterLifecycle,
    AdapterLifecycleSnapshot,
    AdapterLifecycleState,
)
from manga_director.adapters.llm_factory import LLMFactory
from manga_director.adapters.llm_provider import (
    LLMProvider,
    LLMResult,
    PromptRequest,
    PromptResponse,
)
from manga_director.adapters.mock_image_generator import MockImageGenerator
from manga_director.adapters.runtime import (
    AdapterRuntimeReport,
    ImageBackendRuntime,
    LLMProviderRuntime,
)
from manga_director.adapters.runtime_models import (
    AdapterHealth,
    AdapterMetadata,
    AdapterWarmupReport,
    ProviderFallbackPolicy,
)

__all__ = [
    "AdapterHealth",
    "AdapterLifecycle",
    "AdapterLifecycleSnapshot",
    "AdapterLifecycleState",
    "AdapterMetadata",
    "AdapterWarmupReport",
    "AdapterRuntimeReport",
    "ImageGenerator",
    "ImageGeneratorFactory",
    "ImageBackendRuntime",
    "ImageResult",
    "LLMFactory",
    "LLMProviderRuntime",
    "LLMProvider",
    "LLMResult",
    "MockImageGenerator",
    "PromptRequest",
    "PromptResponse",
    "ProviderFallbackPolicy",
]
