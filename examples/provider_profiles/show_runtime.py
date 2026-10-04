"""Inspect provider metadata and diagnostics without a network provider call."""

from manga_director.adapters import LLMProviderRuntime

if __name__ == "__main__":
    print(LLMProviderRuntime().report().to_markdown())
