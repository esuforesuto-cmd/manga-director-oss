"""Contracts for read-only v4 Creative Operating System governance."""

from __future__ import annotations

from pathlib import Path

from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production import V4GovernanceService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _service() -> tuple[V4GovernanceService, InMemoryRepository]:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="governance-pilot",
            title="Governance Pilot",
            chapters=[Chapter(id="one", title="One", page_numbers=[1])],
            pages=[Page(page_number=1, storyboard={"panels": []})],
            metadata={"reference": "redacted", "world": "redacted"},
        )
    )
    return V4GovernanceService(repository), repository


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "governance-pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}, "prompt": {"text": "redacted"}},
        metadata={"workflow_history": [{"step": "prompt", "to": "PromptBuilt"}]},
    )


def test_workspace_governance_is_observational_and_never_enforces_policy() -> None:
    service, repository = _service()

    dashboard = service.workspace("governance-pilot", _context())

    assert dashboard.analysis_only is True
    assert dashboard.policy.policy_persisted is False
    assert dashboard.policy.policy_enforced is False
    assert dashboard.compliance.remediation_performed is False
    assert dashboard.audit.audit_persisted is False
    assert dashboard.audit.workspace_changed is False
    assert dashboard.summary.automatic_action_taken is False
    assert repository.load("governance-pilot").metadata["world"] == "redacted"


def test_memory_governance_cannot_retain_change_or_remediate_memory() -> None:
    service, _ = _service()

    dashboard = service.memory("governance-pilot", _context())

    assert dashboard.analysis_only is True
    assert dashboard.policy.policy_enforced is False
    assert dashboard.compliance.retention_changed is False
    assert dashboard.audit.evidence_changed is False
    assert dashboard.retention.retention_persisted is False
    assert dashboard.retention.retention_enforced is False
    assert dashboard.summary.automatic_action_taken is False


def test_graph_governance_cannot_repair_or_persist_graph_evidence() -> None:
    service, _ = _service()

    dashboard = service.graph("governance-pilot", _context())

    assert dashboard.analysis_only is True
    assert dashboard.policy.policy_enforced is False
    assert dashboard.integrity.consistent is True
    assert dashboard.integrity.repair_performed is False
    assert dashboard.integrity.graph_changed is False
    assert dashboard.compliance.remediation_performed is False
    assert dashboard.audit.audit_persisted is False
    assert dashboard.automatic_action_taken is False


def test_quality_governance_cannot_generate_complete_review_or_approve() -> None:
    service, _ = _service()

    dashboard = service.quality("governance-pilot", _context())

    assert dashboard.analysis_only is True
    assert dashboard.policy.policy_enforced is False
    assert dashboard.editorial.review_completed is False
    assert dashboard.editorial.approval_granted is False
    assert dashboard.editorial.remediation_performed is False
    assert dashboard.audit.audit_persisted is False
    assert dashboard.audit.quality_changed is False
    assert dashboard.summary.quality_enforced is False
    assert dashboard.summary.automatic_action_taken is False


def test_governance_integration_produces_only_human_review_dtos() -> None:
    service, _ = _service()
    context = _context()

    reports = (
        service.workspace("governance-pilot", context),
        service.memory("governance-pilot", context),
        service.graph("governance-pilot", context),
        service.quality("governance-pilot", context),
    )

    assert all(report.analysis_only is True for report in reports)


def test_v4_governance_docs_examples_and_benchmarks_are_available() -> None:
    assets = (
        "docs/CREATIVE_WORKSPACE_GOVERNANCE.md",
        "docs/CREATIVE_MEMORY_GOVERNANCE.md",
        "docs/CREATIVE_GRAPH_GOVERNANCE.md",
        "docs/CREATIVE_QUALITY_GOVERNANCE.md",
        "docs/V4_ITERATION_3_GOVERNANCE_REPORT.md",
        "examples/workspace_governance/v4_governance.py",
        "examples/memory_governance/v4_governance.py",
        "examples/graph_governance/v4_governance.py",
        "examples/quality_governance/v4_governance.py",
        "benchmarks/governance_dashboard_v4.py",
        "benchmarks/policy_validation_v4.py",
        "benchmarks/graph_integrity_v4.py",
        "benchmarks/quality_governance_v4.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
