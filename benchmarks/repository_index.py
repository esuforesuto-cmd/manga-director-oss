"""Measure metadata-index and selective-read repository operations."""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

if __package__ in {None, ""}:  # Supports direct ``python benchmarks/...`` execution.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.large_project import make_large_project
from manga_director.repositories import LocalFileRepository


def run(*, root: Path | None = None) -> float:
    """Measure a supplied test directory or an isolated local directory."""

    if root is not None:
        return _run(root)
    with TemporaryDirectory(ignore_cleanup_errors=True) as temporary_root:
        return _run(Path(temporary_root))


def _run(root: Path) -> float:
    repository = LocalFileRepository(root=root)
    project = make_large_project()
    repository.save(project)
    started = perf_counter()
    repository.list_metadata(limit=10)
    repository.load_page(project.id, 120)
    repository.load_history(project.id, 120, limit=2)
    return perf_counter() - started


if __name__ == "__main__":
    print(f"repository_index: {run():.6f}s")
