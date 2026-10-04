"""Inspect the local lifecycle state of registered LLM providers."""

from manga_director.adapters import LLMProviderRuntime

runtime = LLMProviderRuntime()
for snapshot in runtime.initialize():
    print(snapshot.name, snapshot.state)
for snapshot in runtime.health_snapshot():
    print(snapshot.name, snapshot.state)
