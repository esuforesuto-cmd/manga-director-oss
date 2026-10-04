"""Read-only unified platform governance for human review."""

from __future__ import annotations

from pydantic import Field

from manga_director.platform.dashboard import UnifiedPlatformDashboardDTO
from manga_director.production.director import DirectorModel


class UnifiedPlatformPolicyDTO(DirectorModel):
    policy_id: str = "unified-platform-policy"
    state_machine_authoritative: bool = True
    one_page_scope_required: bool = True
    persisted_storyboard_required: bool = True
    completed_quality_review_required: bool = True
    human_approval_required: bool = True
    policy_enforced: bool = False
    policy_persisted: bool = False


class UnifiedPlatformComplianceDTO(DirectorModel):
    policy_id: str
    context_reference_count: int = Field(default=0, ge=0)
    legacy_contract_preserved: bool = True
    workflow_invariants_referenced: bool = True
    compliance_confirmed: bool = False
    enforcement_action_taken: bool = False


class UnifiedPlatformGovernanceSummary(DirectorModel):
    human_review_required: bool = True
    policy_count: int = Field(default=1, ge=0)
    automatic_action_taken: bool = False


class UnifiedPlatformGovernanceReport(DirectorModel):
    dashboard: UnifiedPlatformDashboardDTO
    policy: UnifiedPlatformPolicyDTO
    compliance: UnifiedPlatformComplianceDTO
    summary: UnifiedPlatformGovernanceSummary
    planning_only: bool = True


class UnifiedPlatformGovernanceService:
    """Creates policy evidence without enforcing, persisting, or approving it."""

    def report(self, dashboard: UnifiedPlatformDashboardDTO) -> UnifiedPlatformGovernanceReport:
        policy = UnifiedPlatformPolicyDTO()
        return UnifiedPlatformGovernanceReport(
            dashboard=dashboard,
            policy=policy,
            compliance=UnifiedPlatformComplianceDTO(
                policy_id=policy.policy_id,
                context_reference_count=len(dashboard.context_intelligence.context.references),
            ),
            summary=UnifiedPlatformGovernanceSummary(),
        )

