"""Contracts for v5.7 Production Platform v1 orchestration diagnostics."""

from __future__ import annotations

from pathlib import Path

import pytest

from manga_director.domain.events import EventType, WorkflowEvent
from manga_director.domain.state_machine import PageState
from manga_director.production import (
    PluginLifecycleDescriptorDTO,
    ProductionTemplateDTO,
    V57ProductionOrchestrator,
)
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "volume-1-page-1"},
        state=PageState.APPROVED,
        artifacts={
            PageState.STORYBOARDED.value: {"panels": []},
            PageState.GENERATED.value: {"image": "reference"},
            PageState.QUALITY_CHECKED.value: {"status": "passed"},
        },
        metadata={
            "story_context": {"beat": "resolution"},
            "character_context": {"hero": "Aki"},
            "world_context": {"location": "station"},
            "timeline_context": {"scene": 8},
            "automation_templates": ["approved-export"],
            "automation_rules": ["human-review-boundary"],
            "workflow_history": [{"step": "approval"}],
            "print_export": {"trim_size": "A5", "dpi": 600},
            "web_export": {"format": "png", "width": 1600},
            "ebook_export": {"format": "epub", "reading_direction": "rtl"},
            "publishing_metadata": {"title": "Pilot", "language": "ja", "rights": "creator"},
        },
        events=[WorkflowEvent(event_type=EventType.PAGE_APPROVED)],
    )


def test_end_to_end_production_platform_is_ready_without_automation_execution() -> None:
    context = _context()
    template = ProductionTemplateDTO(
        template_id="approved-export",
        page_reference="volume-1-page-1",
        required_evidence=("Storyboarded", "QualityChecked"),
    )
    plugin = PluginLifecycleDescriptorDTO(
        plugin_name="layout-tools", version="1.0", enabled=True, active=True
    )

    report = V57ProductionOrchestrator().production_platform(
        "volume-1", context, templates=(template,), plugins=(plugin,)
    )

    assert report.end_to_end_ready is True
    assert report.production_pipeline.summary.workflow_changed is False
    assert report.export.summary.publication_started is False
    assert report.automation.pipeline.automation_ready is True
    assert report.automation.pipeline.execution_dispatched is False
    assert report.plugins.lifecycle_action_performed is False
    assert report.events.publish_performed is False
    assert report.scheduler.task.task_scheduled is False
    assert report.snapshot.restore_performed is False


def test_automation_pipeline_requires_reusable_template_rule_and_evidence_references() -> None:
    context = _context().model_copy(update={"metadata": {}})

    report = V57ProductionOrchestrator().automation_pipeline("volume-1", context)

    assert report.pipeline.automation_ready is False
    assert "automation template reference is required" in report.findings
    assert report.pipeline.workflow_mutated is False


def test_plugin_lifecycle_manager_only_summarizes_caller_supplied_statuses() -> None:
    report = V57ProductionOrchestrator().plugin_lifecycle(
        (
            PluginLifecycleDescriptorDTO(
                plugin_name="zeta", version="1.0", enabled=True, active=False
            ),
            PluginLifecycleDescriptorDTO(
                plugin_name="alpha", version="2.0", enabled=True, active=True
            ),
        )
    )

    assert tuple(plugin.plugin_name for plugin in report.plugins) == ("alpha", "zeta")
    assert report.enabled_plugin_count == 2
    assert report.active_plugin_count == 1
    assert report.lifecycle_owner == "existing_plugin_manager"
    assert report.lifecycle_action_performed is False


def test_event_bus_and_task_scheduler_are_diagnostic_only() -> None:
    context = _context()
    orchestrator = V57ProductionOrchestrator()

    events = orchestrator.event_bus(context)
    scheduler = orchestrator.task_scheduler("volume-1", context)

    assert events.event_count == 1
    assert events.events[0].event_type == EventType.PAGE_APPROVED.value
    assert events.publish_performed is False
    assert scheduler.eligible_for_existing_scheduler is False
    assert scheduler.task.task_dispatched is False


def test_snapshot_restore_is_eligible_but_never_performed() -> None:
    report = V57ProductionOrchestrator().workspace_snapshot("volume-1", _context())

    assert report.restore_eligible is True
    assert report.snapshot.snapshot_persisted is False
    assert report.restore_performed is False
    assert report.workflow_mutated is False


def test_production_analytics_is_read_only_and_reports_export_readiness() -> None:
    context = _context()
    orchestrator = V57ProductionOrchestrator()
    report = orchestrator.production_platform("volume-1", context).analytics

    assert report.analytics.export_eligible is True
    assert report.analytics.quality_review_completed is True
    assert report.analytics.analytics_persisted is False
    assert report.recommendations == ()


def test_orchestrator_rejects_multi_page_context() -> None:
    context = _context().model_copy(update={"page": {"pages": [{"id": "one"}, {"id": "two"}]}})

    with pytest.raises(ValueError, match="exactly one Page"):
        V57ProductionOrchestrator().production_platform("volume-1", context)


def test_v5_7_orchestrator_keeps_delivery_repository_and_runtime_boundaries_out() -> None:
    source = (ROOT / "src/manga_director/production/v5_7_production_platform.py").read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "manga_director.api",
        "manga_director.cli",
        "manga_director.mcp",
        "manga_director.repositories",
        "workflow.engine",
        ".execute(",
        ".advance(",
        "save(",
        ".publish(",
        ".load(",
    ):
        assert forbidden not in source


def test_v5_7_production_platform_docs_are_available() -> None:
    documents = (
        "docs/PRODUCTION_ORCHESTRATOR.md",
        "docs/AUTOMATION_PIPELINE.md",
        "docs/PLUGIN_LIFECYCLE_MANAGER.md",
        "docs/EVENT_BUS.md",
        "docs/TASK_SCHEDULER.md",
        "docs/PRODUCTION_ANALYTICS.md",
        "docs/WORKSPACE_SNAPSHOT_MANAGER.md",
    )

    assert all((ROOT / document).is_file() for document in documents)
