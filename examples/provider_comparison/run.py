"""Compare Provider metadata and local construction health without a request."""

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import ProviderOptimizer, ProviderOrchestrator

report = ProviderOptimizer(
    LLMProviderRuntime(), ProviderOrchestrator(LLMProviderRuntime())
).compare(("text",))
print(report.to_markdown())
