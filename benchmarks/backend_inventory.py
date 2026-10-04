"""Image backend inventory timing without image generation."""

from __future__ import annotations

from time import perf_counter

from manga_director.adapters import ImageBackendRuntime
from manga_director.production import BackendManagement


def run() -> float:
    started = perf_counter()
    assert BackendManagement(ImageBackendRuntime()).inventory().backends
    return perf_counter() - started
