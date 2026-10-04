"""Resolve a provider alias through the Runtime/Factory boundary."""

from manga_director.adapters import LLMFactory, LLMProviderRuntime

if __name__ == "__main__":
    provider_name = LLMProviderRuntime().resolve("default")
    print(LLMFactory.create(provider_name).__class__.__name__)
