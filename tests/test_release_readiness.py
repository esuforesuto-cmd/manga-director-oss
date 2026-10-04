"""Contracts for the read-only v2.5 Iteration 3 readiness facade."""

from __future__ import annotations

from pathlib import Path

from manga_director.cli.config import AppConfig
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production import (
    QualityAutomation,
    ReleaseReadiness,
    RepositoryMaintenance,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _service() -> ReleaseReadiness:
    repository = InMemoryRepository()
    repository.save(Project(id="release", title="Release", pages=[Page(page_number=1)]))
    return ReleaseReadiness(
        quality=QualityAutomation(repository=repository, configuration=AppConfig(), root=ROOT),
        maintenance=RepositoryMaintenance(repository),
        root=ROOT,
    )


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "one"},
        state=PageState.GENERATED,
        artifacts={PageState.STORYBOARDED.value: {"panels": []}},
    )


def test_release_readiness_generates_a_transport_neutral_checklist() -> None:
    report = _service().release_readiness_report(_context(), "release")

    assert report.ready is True
    assert report.checklist.ready is True
    assert "# Release Readiness" in report.to_markdown()


def test_artifact_and_version_validation_use_the_single_package_version_source() -> None:
    service = _service()

    artifacts = service.artifact_verification()
    version = service.version_consistency_validation()

    assert artifacts.valid is True
    assert artifacts.typed_marker_present is True
    assert version.valid is True


def test_repository_health_is_read_only_and_reports_maintenance_evidence() -> None:
    report = _service().repository_health_report("release")

    assert report.healthy is True
    assert report.maintenance.statistics.projects == 1
    assert report.recommendations


def test_oss_readiness_checks_governance_without_remote_operations() -> None:
    report = _service().oss_readiness_report()

    assert report.ready is True
    assert report.governance.valid is True
    assert report.community.details["network_or_github_operation"] is False


def test_dependency_lifecycle_and_maintenance_reports_are_renderable() -> None:
    service = _service()
    dependencies = service.dependency_lifecycle_report()
    maintenance = service.maintenance_report("release")

    assert dependencies.license_report_present is True
    assert dependencies.policy_present is True
    assert maintenance.maintainable is True
    assert "# Maintenance Report" in maintenance.to_markdown()


def test_executive_dashboard_composes_reliability_maintenance_release_and_oss_reports() -> None:
    dashboard = _service().executive_dashboard(_context(), "release")

    assert dashboard.ready is True
    assert dashboard.reliability.recovery.details["persisted_state_changed"] is False
    assert "# Executive Dashboard" in dashboard.to_markdown()
