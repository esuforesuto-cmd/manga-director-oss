"""Measure indexed SQLite metadata and selective page queries."""

from __future__ import annotations

import sys
from pathlib import Path
from time import perf_counter

if __package__ in {None, ""}:  # Supports direct ``python benchmarks/...`` execution.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.large_project import make_large_project
from manga_director.repositories import SQLiteRepository


def run() -> float:
    repository = SQLiteRepository()
    repository.create_schema()
    project = make_large_project()
    repository.save(project)
    started = perf_counter()
    repository.list_metadata(limit=10)
    repository.load_page(project.id, 120)
    repository.load_history(project.id, 120, limit=2)
    return perf_counter() - started


if __name__ == "__main__":
    print(f"database_query: {run():.6f}s")
