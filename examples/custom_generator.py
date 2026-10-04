"""Register a provider without changing ImageAgent, WorkflowEngine, or CLI code."""

import logging

from manga_director import ImageGenerator, ImageResult
from manga_director.adapters.factory import ImageGeneratorFactory

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class StudioGenerator(ImageGenerator):
    def generate(self, prompt: str) -> ImageResult:
        return ImageResult(
            success=True,
            image_path="studio://page.png",
            metadata={"prompt_length": len(prompt)},
            provider="studio",
            elapsed_time=0.0,
            messages=["Studio fixture generated."],
        )


ImageGeneratorFactory.register("studio", StudioGenerator)
LOGGER.info("Providers: %s", ImageGeneratorFactory.available())
