"""Inspect deterministic Provider metadata; no Provider request is sent."""

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import ProviderOrchestrator

report = ProviderOrchestrator(LLMProviderRuntime()).select(("text", "deterministic"))
print(report.to_markdown())
