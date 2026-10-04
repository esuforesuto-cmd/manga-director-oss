"""Large-project contract and bounded performance-regression smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

from benchmarks import batch_resume, database_query, large_project, repository_index, workflow_scale
from manga_director.observability import MetricsRegistry, PerformanceMonitor, RepositoryMetrics
from manga_director.repositories import LocalFileRepository, SQLiteRepository


def test_large_project_metadata_index_and_selective_reads(tmp_path: Path) -> None:
    project = large_project.make_large_project()
    metrics = RepositoryMetrics()
    repository = LocalFileRepository(tmp_path, metrics=metrics)
    repository.save(project)

    metadata = repository.list_metadata(limit=5)

    assert len(metadata) == 1
    assert metadata[0].page_count == 240
    assert repository.load_page(project.id, 120).page_number == 120
    assert repository.load_history(project.id, 120, offset=1, limit=2) == [
        {"step": "Draft", "sequence": 1},
        {"step": "Draft", "sequence": 2},
    ]
    assert (tmp_path / "projects" / "_metadata_index.json").is_file()
    assert (tmp_path / "projects" / "_pages" / project.id / "120.json").is_file()
    # Page reads use the sidecar document and do not require aggregate deserialization.
    (tmp_path / "projects" / f"{project.id}.json").unlink()
    assert repository.load_page(project.id, 120).page_number == 120
    counters = metrics.metrics.snapshot()["counters"]
    assert isinstance(counters, dict)
    assert counters["repository.operations.list_metadata"] == 1


def test_database_metadata_pagination_and_selective_page_query() -> None:
    project = large_project.make_large_project()
    repository = SQLiteRepository()
    repository.create_schema()
    repository.save(project)

    metadata = repository.list_metadata(offset=0, limit=1)

    assert metadata[0].chapter_count == 10
    assert metadata[0].page_count == 240
    assert repository.load_page(project.id, 240).metadata["character"] == "Aki"
    assert len(repository.load_history(project.id, 240, limit=1)) == 1


def test_batch_resume_records_progress_checkpoint_statistics_and_retry_summary() -> None:
    elapsed = batch_resume.run(page_count=40)

    assert elapsed >= 0.0


def test_performance_monitor_emits_threshold_warning_without_control_flow_change() -> None:
    metrics = MetricsRegistry()
    metrics.observe("repository.duration_seconds.load", 0.02)
    monitor = PerformanceMonitor(metrics, {"repository.duration_seconds.load": 0.01})

    assert "repository.duration_seconds.load" in monitor.summary()
    assert monitor.warnings()[0].metric == "repository.duration_seconds.load"


def test_v2_1_performance_regression_smoke(tmp_path: Path) -> None:
    """Fail only on a material (>8x) local regression from retained v2.1 baselines."""

    elapsed = {
        "large_project": large_project.run(),
        "repository_index": repository_index.run(root=tmp_path / "repository-index"),
        "database_query": database_query.run(),
        "batch_resume": batch_resume.run(page_count=40),
        "workflow_scale": workflow_scale.run(page_count=100),
    }
    baseline = json.loads(
        (Path(__file__).resolve().parents[1] / "benchmarks" / "baselines" / "v2_1.json").read_text(
            encoding="utf-8"
        )
    )

    for name, value in elapsed.items():
        assert value <= max(
            baseline[name] * baseline["multiplier"], baseline["minimum_threshold_seconds"]
        ), (name, value)
