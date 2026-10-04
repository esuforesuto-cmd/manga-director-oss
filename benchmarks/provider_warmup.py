"""Metadata-only provider warmup timing."""

from __future__ import annotations

from time import perf_counter

from manga_director.adapters import LLMProviderRuntime


def run() -> float:
    """Warm local provider lifecycle state without LLM invocation."""

    runtime = LLMProviderRuntime()
    started = perf_counter()
    assert runtime.warmup().ready is True
    return perf_counter() - started
