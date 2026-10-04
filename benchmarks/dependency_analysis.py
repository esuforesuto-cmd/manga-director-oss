"""Smoke benchmark for declared dependency lifecycle analysis."""

from __future__ import annotations

from release_validation import _service


def run() -> int:
    return len(_service().dependency_lifecycle_report().runtime_dependencies)


if __name__ == "__main__":
    print(f"runtime_dependencies={run()}")
