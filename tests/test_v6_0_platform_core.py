"""Validation for the read-only v6.0 Platform Kernel completion layer."""

from __future__ import annotations

from pathlib import Path

import pytest

from manga_director.domain.state_machine import PageState
from manga_director.production import (
    CollaborationAssignmentDTO,
    ExtensionFrameworkDTO,
    GovernanceControlDTO,
    KnowledgeCoreReferenceDTO,
    MarketplaceListingDTO,
    PlatformPolicyDTO,
    ProjectHubReferenceDTO,
    SDKCapabilityDTO,
    ServiceRegistryEntryDTO,
    V60CreativeProductionPlatformCoreService,
    V60UnifiedContextReferenceDTO,
    WorkspaceHubReferenceDTO,
)
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "volume-1-page-1"},
        state=PageState.QUALITY_CHECKED,
        artifacts={
            PageState.STORYBOARDED.value: {"panels": []},
            PageState.QUALITY_CHECKED.value: {"status": "passed"},
        },
        metadata={
            "story_context": {"beat": "resolution"},
            "character_context": {"hero": "Aki"},
            "world_context": {"location": "station"},
            "timeline_context": {"scene": 8},
        },
    )


def _knowledge() -> tuple[KnowledgeCoreReferenceDTO, ...]:
    return (
        KnowledgeCoreReferenceDTO(
            knowledge_id="story:volume-1",
            project_id="volume-1",
            kind="story",
            source_reference="story_context",
            provenance="workflow-metadata",
        ),
    )


def _platform_report():
    return V60CreativeProductionPlatformCoreService().platform_core(
        "volume-1",
        _context(),
        projects=(ProjectHubReferenceDTO(project_id="volume-1", title="One"),),
        workspaces=(
            WorkspaceHubReferenceDTO(
                workspace_id="workspace:volume-1", project_id="volume-1", label="One"
            ),
        ),
        knowledge=_knowledge(),
        assignments=(
            CollaborationAssignmentDTO(
                assignment_id="review:one",
                project_id="volume-1",
                workspace_id="workspace:volume-1",
                role="reviewer",
                assignee_reference="editor-1",
            ),
        ),
        services=(
            ServiceRegistryEntryDTO(
                service_id="knowledge-graph",
                capability="provenance-projection",
                owner="knowledge_engine",
                compatibility="v6_foundation",
            ),
        ),
        context_references=(
            V60UnifiedContextReferenceDTO(
                domain="knowledge",
                context_id="story:volume-1",
                source_module="knowledge_engine",
                source_reference="story_context",
            ),
        ),
        extensions=(
            ExtensionFrameworkDTO(
                extension_id="extension:analytics",
                name="Analytics Extension",
                extension_type="analytics",
                compatibility="v6_foundation",
            ),
        ),
        sdk_capabilities=(
            SDKCapabilityDTO(
                capability_id="sdk:python:platform-kernel",
                surface="python",
                source_reference="manga_director.production",
                compatibility="v6_foundation",
            ),
        ),
        marketplace_listings=(
            MarketplaceListingDTO(
                listing_id="listing:analytics",
                name="Analytics Extension",
                listing_type="extension",
                compatibility="v6_foundation",
            ),
        ),
        policies=(PlatformPolicyDTO(policy_id="policy:extensions", scope="extension"),),
        governance_controls=(
            GovernanceControlDTO(
                control_id="control:extension-review",
                policy_id="policy:extensions",
                area="extension",
            ),
        ),
    )


def test_platform_core_composes_all_areas_without_automatic_action() -> None:
    report = _platform_report()

    assert report.enterprise_operation_ready is True
    assert report.automatic_action_taken is False
    assert report.kernel.kernel.kernel_started is False
    assert report.kernel.kernel.runtime_changed is False
    assert report.kernel.intelligence.foundation.production.production.page_count == 1


def test_unified_context_manager_reuses_context_without_persisting_or_prompting() -> None:
    context = _context()
    before = context.model_dump()
    report = V60CreativeProductionPlatformCoreService().unified_context_manager(
        "volume-1", context
    )

    assert report.context.page_count == 1
    assert report.context_engine.complete is True
    assert report.context_mutated is False
    assert report.prompt_generated is False
    assert context.model_dump() == before


def test_extension_and_sdk_foundations_are_additive_and_observational() -> None:
    report = _platform_report()

    assert report.extensions.compatible is True
    assert report.extensions.extensions[0].extension_loaded is False
    assert report.sdk.compatible is True
    assert report.sdk.sdk_published is False
    assert report.sdk.public_api_changed is False


def test_marketplace_and_policy_frameworks_never_publish_or_enforce() -> None:
    report = _platform_report()

    assert report.marketplace.valid is True
    assert report.marketplace.marketplace_contacted is False
    assert report.marketplace.marketplace_mutated is False
    assert report.policy.valid is True
    assert report.policy.enforcement_performed is False


def test_governance_reports_missing_policy_without_applying_a_control() -> None:
    report = V60CreativeProductionPlatformCoreService().governance_framework(
        (
            GovernanceControlDTO(
                control_id="control:missing-policy",
                policy_id="policy:missing",
                area="workflow",
            ),
        )
    )

    assert report.valid is False
    assert report.missing_policy_ids == ("policy:missing",)
    assert report.compliance_decision_automated is False


def test_observability_uses_derived_metrics_without_telemetry_or_alerts() -> None:
    report = _platform_report().observability

    assert report.metric_count == 3
    assert report.dashboard_ready is True
    assert report.telemetry_persisted is False
    assert report.alert_dispatched is False


def test_platform_core_rejects_multi_page_context() -> None:
    context = _context().model_copy(update={"page": {"pages": [{"id": "one"}, {"id": "two"}]}})

    with pytest.raises(ValueError, match="exactly one Page"):
        V60CreativeProductionPlatformCoreService().platform_core("volume-1", context)


def test_platform_core_keeps_delivery_repository_and_execution_boundaries_out() -> None:
    source = (ROOT / "src/manga_director/production/v6_0_platform_core.py").read_text(
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


def test_platform_core_documentation_is_available() -> None:
    documents = (
        "docs/PLATFORM_KERNEL.md",
        "docs/UNIFIED_CONTEXT_MANAGER.md",
        "docs/EXTENSION_FRAMEWORK.md",
        "docs/SDK_FOUNDATION.md",
        "docs/MARKETPLACE_FRAMEWORK.md",
        "docs/POLICY_ENGINE.md",
        "docs/GOVERNANCE_FRAMEWORK.md",
        "docs/OBSERVABILITY_PLATFORM.md",
    )

    assert all((ROOT / document).is_file() for document in documents)
