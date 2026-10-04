"""Contracts for the v4.8 Unified Platform foundation."""

from __future__ import annotations

from pathlib import Path

import pytest

from manga_director.domain.state_machine import PageState
from manga_director.production import (
    UnifiedServiceRegistry,
    V48ServiceDescriptorDTO,
    V48UnifiedPlatformFoundationService,
)
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
        metadata={"provenance": "human"},
    )


def test_unified_platform_is_one_page_scoped_and_non_operational() -> None:
    report = V48UnifiedPlatformFoundationService().unified_platform("pilot", _context())

    assert report.planning_only is True
    assert report.scope.page_count == 1
    assert report.scope.state_machine_authoritative is True
    assert report.scope.scope_persisted is False
    assert report.scope.workflow_mutated is False
    assert report.summary.service_count == 6
    assert report.summary.aggregate_persisted is False
    assert report.summary.automatic_action_taken is False
    assert all(service.public_contract_preserved for service in report.services)
    assert all(service.runtime_registered is False for service in report.services)
    assert all(service.service_invoked is False for service in report.services)


def test_modular_runtime_is_declarative_without_dynamic_loading_or_activation() -> None:
    report = V48UnifiedPlatformFoundationService().modular_runtime()

    assert report.planning_only is True
    assert report.summary.module_count == 7
    assert report.summary.existing_runtime_replaced is False
    assert report.summary.plugin_execution_enabled is False
    assert report.summary.automatic_action_taken is False
    assert all(module.core_dependency_direction_preserved for module in report.modules)
    assert all(module.dynamically_loaded is False for module in report.modules)
    assert all(module.runtime_activated is False for module in report.modules)


def test_service_registry_only_records_explicit_local_metadata() -> None:
    registry = UnifiedServiceRegistry()
    descriptor = V48ServiceDescriptorDTO(
        service_id="example",
        module_id="example-module",
        capability_names=("report",),
    )

    registry.register(descriptor)
    report = registry.report()

    assert registry.get("example") == descriptor
    assert report.planning_only is True
    assert report.summary.service_count == 1
    assert report.summary.external_discovery_performed is False
    assert report.summary.runtime_routing_changed is False
    with pytest.raises(ValueError, match="duplicate service descriptor"):
        registry.register(descriptor)


def test_lifecycle_manager_is_descriptive_and_preserves_workflow_gates() -> None:
    report = V48UnifiedPlatformFoundationService().lifecycle_manager("pilot", _context())

    assert report.planning_only is True
    assert report.scope.page_count == 1
    assert report.summary.reference_count == 2
    assert report.summary.retention_policy_enforced is False
    assert report.summary.recovery_attempted is False
    assert report.summary.record_mutated is False
    assert all(reference.lifecycle_persisted is False for reference in report.references)
    assert all(reference.state_transitioned is False for reference in report.references)


def test_operational_intelligence_is_read_only_and_has_no_telemetry_or_action() -> None:
    report = V48UnifiedPlatformFoundationService().operational_intelligence("pilot", _context())

    assert report.planning_only is True
    assert report.scope.page_count == 1
    assert report.summary.signal_count == 6
    assert report.summary.presentation_dependency is False
    assert report.summary.report_persisted is False
    assert report.summary.monitoring_started is False
    assert report.summary.alert_sent is False
    assert report.summary.automatic_action_taken is False
    assert all(signal.evidence_supplied is False for signal in report.signals)
    assert all(signal.telemetry_collected is False for signal in report.signals)
    assert all(signal.operational_action_taken is False for signal in report.signals)


def test_v4_8_foundation_keeps_delivery_repository_and_runtime_boundaries_out_of_module() -> None:
    source = (ROOT / "src/manga_director/production/v4_8_unified_foundation.py").read_text(
        encoding="utf-8"
    )

    assert "manga_director.api" not in source
    assert "manga_director.cli" not in source
    assert "manga_director.mcp" not in source
    assert "manga_director.repositories" not in source
    assert "save(" not in source
    assert ".execute(" not in source
    assert "workflow_engine" not in source


def test_v4_8_foundation_docs_report_quality_gates_and_debt_are_available() -> None:
    assets = (
        "docs/UNIFIED_PLATFORM_FOUNDATION.md",
        "docs/MODULAR_RUNTIME_FOUNDATION.md",
        "docs/SERVICE_REGISTRY.md",
        "docs/LIFECYCLE_MANAGER.md",
        "docs/OPERATIONAL_INTELLIGENCE_FOUNDATION.md",
        "docs/V4_8_ITERATION_1_UNIFIED_PLATFORM_FOUNDATION_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    for gate in (
        "Unified Platform Foundation Validation",
        "Modular Runtime Foundation Validation",
        "Service Registry Validation",
        "Lifecycle Manager Validation",
        "Operational Intelligence Foundation Validation",
    ):
        assert gate in gates
    for category in (
        "Unified Platform Foundation",
        "Modular Runtime Foundation",
        "Service Registry",
        "Lifecycle Manager",
        "Operational Intelligence Foundation",
    ):
        assert category in debt
