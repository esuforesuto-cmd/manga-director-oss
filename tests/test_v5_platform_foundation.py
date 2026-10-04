"""v5 One Creative Platform foundation contracts."""

from __future__ import annotations

import pytest

from manga_director.domain.state_machine import PageState
from manga_director.platform import (
    UnifiedApiGatewayFoundation,
    UnifiedApiGatewayRequestDTO,
    UnifiedApiSurfaceRequestDTO,
    UnifiedApiSurfaceService,
    UnifiedContextReferenceDTO,
    UnifiedCreativeContextFactory,
    UnifiedPlatformDashboardService,
    UnifiedPlatformFoundationService,
    UnifiedPlatformMaturityService,
    UnifiedPlatformRegistry,
    UnifiedRuntimeFoundationService,
    UnifiedRuntimeOrchestrationService,
    UnifiedSDKFoundation,
    UnifiedServiceDescriptorDTO,
)
from manga_director.workflow import WorkflowContext


def _context() -> WorkflowContext:
    return WorkflowContext(page={"id": "page-1"}, state=PageState.STORYBOARDED)


def _references() -> tuple[UnifiedContextReferenceDTO, ...]:
    return (
        UnifiedContextReferenceDTO(
            domain="workspace",
            context_id="workspace-1",
            source_module="workspace",
            source_reference="workspace:workspace-1",
        ),
        UnifiedContextReferenceDTO(
            domain="knowledge",
            context_id="knowledge-1",
            source_module="knowledge",
            source_reference="knowledge:knowledge-1",
        ),
        UnifiedContextReferenceDTO(
            domain="agent",
            context_id="agent-1",
            source_module="agents",
            source_reference="agent:agent-1",
        ),
        UnifiedContextReferenceDTO(
            domain="production",
            context_id="production-1",
            source_module="production",
            source_reference="production:production-1",
        ),
    )


def test_platform_integration_preserves_one_page_and_owner_boundaries() -> None:
    report = UnifiedPlatformFoundationService().report("project-1", _context(), _references())

    assert report.context.project_id == "project-1"
    assert report.context.page_count == 1
    assert report.context.state_machine_authoritative
    assert report.summary.context_reference_count == 4
    assert report.summary.aggregate_persisted is False
    assert all(module.source_of_truth_transferred is False for module in report.modules)


def test_unified_context_accepts_one_explicit_reference_per_domain() -> None:
    context = UnifiedCreativeContextFactory().create("project-1", _context(), _references())

    assert tuple(reference.domain for reference in context.references) == (
        "workspace",
        "knowledge",
        "agent",
        "production",
    )
    assert all(reference.source_loaded is False for reference in context.references)
    with pytest.raises(ValueError, match="one reference"):
        UnifiedCreativeContextFactory().create(
            "project-1", _context(), (_references()[0], _references()[0])
        )


def test_api_gateway_is_read_only_and_preserves_legacy_contracts() -> None:
    response = UnifiedApiGatewayFoundation().preview(
        UnifiedApiGatewayRequestDTO(project_id="project-1", references=_references()), _context()
    )

    assert response.legacy_contract_preserved
    assert response.route_registered is False
    assert response.response_persisted is False
    assert response.report.context.workflow_mutated is False


def test_runtime_and_sdk_are_declarative_compatible_facades() -> None:
    runtime = UnifiedRuntimeFoundationService().report()
    response = UnifiedSDKFoundation().platform_preview("project-1", _context(), _references())

    assert runtime.summary.module_count == 8
    assert runtime.summary.routing_enabled is False
    assert all(module.dynamically_loaded is False for module in runtime.modules)
    assert response.report.context.page_reference == "page-1"
    assert UnifiedSDKFoundation().runtime_preview() == runtime


def test_unified_context_intelligence_is_advisory_and_non_mutating() -> None:
    report = UnifiedSDKFoundation().context_intelligence("project-1", _context(), _references())

    assert report.coverage.coverage_ratio == 1.0
    assert report.coverage.missing_domains == ()
    assert report.findings == ()
    assert report.context_mutated is False
    assert report.planning_only is True


def test_unified_api_surface_preserves_existing_delivery_contracts() -> None:
    report = UnifiedApiSurfaceService().preview(
        UnifiedApiSurfaceRequestDTO(project_id="project-1", references=_references()), _context()
    )
    registry = UnifiedPlatformRegistry()
    descriptor = UnifiedServiceDescriptorDTO(service_id="preview", module_id="platform")

    registry.register(descriptor)
    assert report.legacy_contract_preserved
    assert report.transport_registered is False
    assert report.registry.service_count == 1
    assert registry.report().services == (descriptor,)
    with pytest.raises(ValueError, match="duplicate unified service descriptor"):
        registry.register(descriptor)


def test_runtime_orchestration_only_returns_a_dependency_order() -> None:
    report = UnifiedRuntimeOrchestrationService().plan()

    assert tuple(stage.module_ids for stage in report.stages) == (
        ("core",),
        ("knowledge", "workspace"),
        ("agent-platform", "production"),
        ("decision", "enterprise"),
        ("ecosystem",),
    )
    assert all(stage.modules_activated is False for stage in report.stages)
    assert report.runtime_entry_points_replaced is False
    assert report.routing_performed is False


def test_dashboard_and_sdk_composes_read_only_platform_views() -> None:
    dashboard = UnifiedPlatformDashboardService().preview("project-1", _context(), _references())
    sdk_dashboard = UnifiedSDKFoundation().dashboard("project-1", _context(), _references())

    assert dashboard.context_intelligence.coverage.coverage_ratio == 1.0
    assert dashboard.dashboard_persisted is False
    assert dashboard.presentation_dependency is False
    assert sdk_dashboard == dashboard


def test_governance_integration_is_human_reviewed_and_non_enforcing() -> None:
    report = UnifiedPlatformMaturityService().report("project-1", _context(), _references())

    assert report.governance.policy.state_machine_authoritative
    assert report.governance.policy.policy_enforced is False
    assert report.governance.compliance.legacy_contract_preserved
    assert report.governance.compliance.compliance_confirmed is False
    assert report.governance.summary.human_review_required


def test_observability_integration_requires_supplied_evidence_without_monitoring() -> None:
    report = UnifiedPlatformMaturityService().report("project-1", _context(), _references())

    assert report.observability.observation_count == 4
    assert report.observability.monitoring_started is False
    assert all(observation.telemetry_collected is False for observation in report.observability.observations)
    assert all(observation.health_probe_executed is False for observation in report.observability.observations)


def test_reliability_integration_makes_unchecked_health_explicit() -> None:
    report = UnifiedPlatformMaturityService().report("project-1", _context(), _references())

    assert report.reliability.component_count == 5
    assert all(component.status == "not_checked" for component in report.reliability.components)
    assert report.reliability.runtime_reconfigured is False
    assert report.reliability.automatic_recovery_taken is False


def test_lifecycle_integration_is_descriptive_and_one_page_scoped() -> None:
    report = UnifiedPlatformMaturityService().report("project-1", _context(), _references())

    assert report.lifecycle.reference_count == 2
    assert all(reference.page_count == 1 for reference in report.lifecycle.references)
    assert all(reference.state_transitioned is False for reference in report.lifecycle.references)
    assert report.lifecycle.lifecycle_owner_transferred is False


def test_developer_experience_validation_is_advisory_and_sdk_available() -> None:
    report = UnifiedSDKFoundation().maturity("project-1", _context(), _references())

    assert report.developer_experience.supported_entry_points == (
        "python",
        "cli",
        "fastapi",
        "mcp",
        "web-ui",
    )
    assert len(report.developer_experience.recommendations) == 2
    assert report.developer_experience.configuration_changed is False
    assert report.developer_experience.tooling_installed is False
    assert report.lts_candidate
