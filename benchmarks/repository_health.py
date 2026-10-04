"""Smoke benchmark for repository health reporting."""

from __future__ import annotations

from release_validation import _service


def run() -> bool:
    return _service().repository_health_report("benchmark").healthy


if __name__ == "__main__":
    print(f"repository_health_valid={run()}")
