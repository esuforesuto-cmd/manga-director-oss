"""Configuration-governance reload timing without file or secret mutation."""

from __future__ import annotations

from time import perf_counter

from manga_director.cli.config import AppConfig, configuration_governance


def run() -> float:
    """Measure a repeatable in-memory configuration validation pass."""

    started = perf_counter()
    report = configuration_governance(AppConfig())
    assert report.compatible is True
    return perf_counter() - started
