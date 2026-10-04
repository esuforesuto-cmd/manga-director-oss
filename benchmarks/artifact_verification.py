"""Smoke benchmark for static release-artifact verification."""

from __future__ import annotations

from release_validation import _service


def run() -> bool:
    return _service().artifact_verification().valid


if __name__ == "__main__":
    print(f"artifact_verification_valid={run()}")
