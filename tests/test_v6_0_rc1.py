"""Release-candidate integration and compatibility contracts for v6.0.0rc1."""

from __future__ import annotations

from pathlib import Path

import manga_director
from manga_director.domain.state_machine import PageState
from manga_director.production import (
    ExtensionFrameworkDTO,
    KnowledgeCoreReferenceDTO,
    MarketplaceListingDTO,
    PlatformPolicyDTO,
    SDKCapabilityDTO,
    V57ProductionPlatformFoundationService,
    V60CreativeProductionPlatformCoreService,
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


def test_rc1_version_and_v5_foundation_contract_remain_available() -> None:
    context = _context()

    assert manga_director.__version__ == "6.0.0"
    v5_report = V57ProductionPlatformFoundationService().foundation("volume-1", context)
    assert v5_report.project.project.page_reference == "volume-1-page-1"
    assert v5_report.project.project.quality_review_completed is True
    assert v5_report.planning_only is True


def test_rc1_end_to_end_platform_is_advisory_and_preserves_one_page_workflow() -> None:
    context = _context()
    before = context.model_dump()
    report = V60CreativeProductionPlatformCoreService().platform_core(
        "volume-1",
        context,
        knowledge=(
            KnowledgeCoreReferenceDTO(
                knowledge_id="story:volume-1",
                project_id="volume-1",
                kind="story",
                source_reference="story_context",
                provenance="workflow-metadata",
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
    )

    assert report.kernel.intelligence.workflow.orchestrator.next_command == "approve"
    assert report.extensions.extensions[0].extension_loaded is False
    assert report.sdk.sdk_published is False
    assert report.marketplace.marketplace_contacted is False
    assert report.policy.enforcement_performed is False
    assert report.observability.telemetry_persisted is False
    assert report.automatic_action_taken is False
    assert context.model_dump() == before


def test_rc1_release_documentation_is_complete() -> None:
    documents = (
        "RELEASE_V6_0_RC1.md",
        "docs/V6_0_RC1_REPORT.md",
        "docs/PLATFORM_INTEGRATION_REPORT.md",
        "docs/SDK_COMPATIBILITY_REPORT.md",
        "docs/EXTENSION_COMPATIBILITY_REPORT.md",
        "docs/GOVERNANCE_REPORT.md",
        "docs/OBSERVABILITY_REPORT.md",
        "docs/QUALITY_GATE_REPORT.md",
        "docs/RELEASE_CHECKLIST.md",
        "docs/KNOWN_ISSUES.md",
    )

    assert all((ROOT / document).is_file() for document in documents)
