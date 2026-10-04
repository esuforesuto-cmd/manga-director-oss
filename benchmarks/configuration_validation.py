"""Configuration governance smoke benchmark."""

from __future__ import annotations

from time import perf_counter

from manga_director.cli.config import AppConfig, configuration_governance


def run(iterations: int = 100) -> float:
    config = AppConfig(profile="enterprise", read_only=True)
    start = perf_counter()
    for _ in range(iterations):
        configuration_governance(config)
    return perf_counter() - start


if __name__ == "__main__":
    print(f"configuration_validation: {run():.6f}s")
