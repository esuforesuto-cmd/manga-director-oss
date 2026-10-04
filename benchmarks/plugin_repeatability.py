"""Measure local Plugin discovery/loading repeatability."""

from __future__ import annotations

from benchmarks.plugin_loading import run as plugin_loading
from benchmarks.repeatability import RepeatabilityResult, measure


def run(runs: int = 5) -> RepeatabilityResult:
    return measure(lambda: plugin_loading(plugin_count=10), runs=runs)


if __name__ == "__main__":
    print(run().model_dump_json())
