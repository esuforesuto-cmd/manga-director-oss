from manga_director.adapters.image_generator import ImageResult


class ComfyUIImageGenerator:
    """ComfyUI API boundary; network behavior is intentionally deferred."""

    def __init__(self, endpoint: str | None = None) -> None:
        self._endpoint = endpoint

    def generate(self, prompt: str) -> ImageResult:
        # TODO(phase-7): submit a ComfyUI workflow, poll its result, and persist the image asset.
        return ImageResult(
            success=False,
            image_path=None,
            metadata={"prompt_length": len(prompt)},
            provider="comfyui",
            elapsed_time=0.0,
            messages=["ComfyUI image generation is an API boundary stub."],
        )
