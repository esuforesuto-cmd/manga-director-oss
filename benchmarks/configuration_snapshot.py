"""Safe runtime configuration snapshot timing."""

from __future__ import annotations

from time import perf_counter

from manga_director.cli.config import AppConfig
from manga_director.production import RuntimeConfiguration


def run() -> float:
    configuration = RuntimeConfiguration(AppConfig())
    started = perf_counter()
    assert configuration.report().governance.integrity_valid is True
    return perf_counter() - started
