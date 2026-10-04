"""Warm registered Provider metadata without sending an LLM request."""

from manga_director.adapters import LLMProviderRuntime


def main() -> None:
    runtime = LLMProviderRuntime()
    print(runtime.warmup().model_dump_json(indent=2))
    print(runtime.fallback_simulation().model_dump_json(indent=2))


if __name__ == "__main__":
    main()
