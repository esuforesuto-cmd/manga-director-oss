"""Provider inventory timing without provider invocation."""

from __future__ import annotations

from time import perf_counter

from manga_director.adapters import LLMProviderRuntime
from manga_director.production import ProviderManagement


def run() -> float:
    started = perf_counter()
    assert ProviderManagement(LLMProviderRuntime()).inventory().recommendation.available is True
    return perf_counter() - started
