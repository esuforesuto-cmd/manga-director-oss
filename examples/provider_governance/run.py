"""Review local Provider governance without invoking a model."""

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.cli.config import AppConfig
from manga_director.production import ProviderGovernance, ProviderOptimizer, ProviderOrchestrator

runtime = LLMProviderRuntime()
report = ProviderGovernance(
    runtime=runtime,
    optimizer=ProviderOptimizer(runtime, ProviderOrchestrator(runtime)),
    configuration=AppConfig(),
).report()
print(report.to_markdown())
