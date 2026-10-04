from manga_director.adapters.image_generator import ImageResult


class MockImageGenerator:
    """Deterministic generator for local execution and unit tests."""

    def generate(self, prompt: str) -> ImageResult:
        return ImageResult(
            success=True,
            image_path="mock://generated-page.png",
            metadata={"prompt_length": len(prompt), "fixture": True},
            provider="mock",
            elapsed_time=0.0,
            messages=["Mock image generated."],
        )
