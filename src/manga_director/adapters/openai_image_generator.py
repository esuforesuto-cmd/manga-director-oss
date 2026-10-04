from manga_director.adapters.image_generator import ImageResult


class OpenAIImageGenerator:
    """OpenAI image API boundary; network behavior is intentionally deferred."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    def generate(self, prompt: str) -> ImageResult:
        # TODO(phase-7): obtain API key securely, send HTTP request, and persist the image asset.
        return ImageResult(
            success=False,
            image_path=None,
            metadata={"prompt_length": len(prompt)},
            provider="openai",
            elapsed_time=0.0,
            messages=["OpenAI image generation is an API boundary stub."],
        )
