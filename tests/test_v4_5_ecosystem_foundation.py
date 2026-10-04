"""Contracts for non-executing v4.5 ecosystem foundations."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.domain.state_machine import PageState
from manga_director.production import (
    V45EcosystemFoundationService,
    V45WorkflowMarketplaceEntryDTO,
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


def test_creative_service_registry_cannot_register_discover_or_invoke() -> None:
    report = V45EcosystemFoundationService().creative_service_registry("pilot", _context())

    assert report.planning_only is True
    assert report.service.page_count == 1
    assert report.service.service_registered is False
    assert report.service.service_invoked is False
    assert report.capability.compatibility_assessed is False
    assert report.registry.registry_persisted is False
    assert report.registry.remote_discovery_enabled is False
    assert report.summary.automatic_action_taken is False


def test_plugin_foundation_preserves_sdk_and_cannot_load_execute_or_grant_permission() -> None:
    report = V45EcosystemFoundationService().plugin_foundation("pilot", _context())

    assert report.planning_only is True
    assert report.plugin.extension_sdk_contract == "existing_sdk_unchanged"
    assert report.plugin.plugin_loaded is False
    assert report.plugin.plugin_executed is False
    assert report.compatibility.permission_granted is False
    assert report.registry.registry_persisted is False
    assert report.registry.remote_discovery_enabled is False


def test_workflow_marketplace_is_one_page_and_cannot_install_execute_publish_or_bill() -> None:
    report = V45EcosystemFoundationService().workflow_marketplace("pilot", _context())

    assert report.planning_only is True
    assert report.marketplace.catalog_persisted is False
    assert report.marketplace.remote_discovery_enabled is False
    assert report.entry.page_count == 1
    assert report.entry.downloaded is False
    assert report.entry.installed is False
    assert report.entry.executed is False
    assert report.policy.state_machine_authoritative is True
    assert report.policy.policy_enforced is False
    assert report.policy.published is False
    assert report.policy.payment_processed is False
    assert report.policy.billing_performed is False


def test_knowledge_exchange_cannot_persist_synchronize_transfer_or_share() -> None:
    report = V45EcosystemFoundationService().knowledge_exchange("pilot", _context())

    assert report.planning_only is True
    assert report.exchange.page_count == 1
    assert report.exchange.exchange_persisted is False
    assert report.exchange.synchronized is False
    assert report.descriptor.redaction_required is True
    assert report.descriptor.ownership_transfered is False
    assert report.policy.human_consent_required is True
    assert report.policy.sharing_approved is False
    assert report.policy.remote_search_enabled is False


def test_federation_registry_cannot_register_connect_authenticate_or_federate() -> None:
    report = V45EcosystemFoundationService().federation_registry("pilot", _context())

    assert report.planning_only is True
    assert report.domain.page_count == 1
    assert report.domain.domain_registered is False
    assert report.domain.network_connected is False
    assert report.peer.authenticated is False
    assert report.peer.transport_connected is False
    assert report.registry.registry_persisted is False
    assert report.registry.federation_enabled is False
    assert report.summary.automatic_action_taken is False


def test_marketplace_entry_rejects_more_than_one_page_scope() -> None:
    with pytest.raises(ValidationError):
        V45WorkflowMarketplaceEntryDTO(entry_id="entry", page_count=2)


def test_v4_5_foundation_keeps_delivery_repository_and_runtime_boundaries_out_of_module() -> None:
    source = (ROOT / "src/manga_director/production/v4_5_ecosystem_foundation.py").read_text(
        encoding="utf-8"
    )

    assert "manga_director.api" not in source
    assert "manga_director.cli" not in source
    assert "manga_director.mcp" not in source
    assert "manga_director.repositories" not in source
    assert "save(" not in source
    assert ".execute(" not in source
    assert "workflow_engine" not in source


def test_v4_5_foundation_docs_report_quality_gates_and_debt_are_available() -> None:
    assets = (
        "docs/CREATIVE_SERVICE_REGISTRY.md",
        "docs/PLUGIN_FOUNDATION.md",
        "docs/WORKFLOW_MARKETPLACE_FOUNDATION.md",
        "docs/KNOWLEDGE_EXCHANGE_FOUNDATION.md",
        "docs/FEDERATION_REGISTRY.md",
        "docs/V4_5_ITERATION_1_ECOSYSTEM_FOUNDATION_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    for gate in (
        "Creative Service Registry Foundation Validation",
        "Plugin Foundation Validation",
        "Workflow Marketplace Foundation Validation",
        "Knowledge Exchange Foundation Validation",
        "Federation Registry Foundation Validation",
    ):
        assert gate in gates
    for category in (
        "Creative Service Registry",
        "Plugin Foundation",
        "Workflow Marketplace Foundation",
        "Knowledge Exchange Foundation",
        "Federation Registry Foundation",
    ):
        assert category in debt
