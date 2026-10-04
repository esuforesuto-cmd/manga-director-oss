"""Measure cached validated configuration reads and environment-safe reload checks."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from manga_director.cli.config import clear_config_cache, load_config


def run(iterations: int = 500) -> float:
    with TemporaryDirectory(ignore_cleanup_errors=True) as root:
        path = Path(root) / "config.yaml"
        path.write_text("repository:\n  root: projects\n", encoding="utf-8")
        clear_config_cache(path)
        started = perf_counter()
        for _ in range(iterations):
            load_config(path)
        return perf_counter() - started


if __name__ == "__main__":
    print(f"configuration_load: {run():.6f}s")
