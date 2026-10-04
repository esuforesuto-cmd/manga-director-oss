"""Measure cached Extension manifest validation without network providers."""

from __future__ import annotations

from time import perf_counter

from manga_director.sdk import ExtensionManifest, ExtensionValidator


def run(iterations: int = 500) -> float:
    validator = ExtensionValidator()
    manifest = ExtensionManifest(
        id="benchmark-extension",
        name="Benchmark Extension",
        version="1.0.0",
        author="manga-director",
        license="MIT",
        description="provider-free benchmark",
        entry_point="manga_director.sdk.extension:Extension",
    )
    started = perf_counter()
    for _ in range(iterations):
        validator.validate(manifest)
    return perf_counter() - started


if __name__ == "__main__":
    print(f"extension_loading: {run():.6f}s")
