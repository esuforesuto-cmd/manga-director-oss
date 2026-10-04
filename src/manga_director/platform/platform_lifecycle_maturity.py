"""v5.5 non-enforcing governance, reliability, policy, and observability reports.

These services compose Lifecycle Intelligence evidence only. They never enforce
policy, install or roll back software, retire a capability, collect telemetry,
recover runtime state, or change workflow execution.
"""

from __future__ import annotations

from manga_director.platform.platform_lifecycle import PlatformLifecycleFoundationRequestDTO
from manga_director.platform.platform_lifecycle_intelligence import (
    LifecycleIntelligenceService,
    MaintenanceDashboardDTO,
)
from manga_director.production.director import DirectorModel


class LifecyclePolicyDTO(DirectorModel):
    policy_id: str
    revision: str
    owner: str
    require_lts_compatibility: bool = True
    require_lifecycle_evidence: bool = True
    human_review_required: bool = True
    enforcement_performed: bool = False


class UpgradePolicyDTO(DirectorModel):
    policy_id: str
    revision: str
    owner: str
    require_lts_compatibility: bool = True
    require_rollback_reference: bool = True
    require_compatibility_evidence: bool = True
    enforcement_performed: bool = False


class MaintenancePolicyDTO(DirectorModel):
    policy_id: str
    revision: str
    owner: str
    require_health_evidence: bool = True
    require_human_maintenance_decision: bool = True
    enforcement_performed: bool = False


class LifecycleGovernanceReport(DirectorModel):
    dashboard: MaintenanceDashboardDTO
    policy: LifecyclePolicyDTO
    lifecycle_policy_compliant: bool = False
    state_machine_authoritative: bool = True
    policy_enforced: bool = False
    automatic_action_taken: bool = False
    planning_only: bool = True


class UpgradeGovernanceReport(DirectorModel):
    dashboard: MaintenanceDashboardDTO
    policy: UpgradePolicyDTO
    upgrade_policy_compliant: bool = False
    lts_compatibility_valid: bool = False
    rollback_reference_present: bool = False
    policy_enforced: bool = False
    upgrade_performed: bool = False
    planning_only: bool = True


class PlatformReliabilityReport(DirectorModel):
    dashboard: MaintenanceDashboardDTO
    metadata_valid: bool = False
    reliability_status: str
    health_check_performed: bool = False
    recovery_attempted: bool = False
    runtime_reconfigured: bool = False
    planning_only: bool = True


class MaintenancePolicyReport(DirectorModel):
    dashboard: MaintenanceDashboardDTO
    policy: MaintenancePolicyDTO
    maintenance_policy_compliant: bool = False
    human_decision_required: bool = True
    policy_enforced: bool = False
    planning_only: bool = True


class LifecycleObservabilityReport(DirectorModel):
    dashboard: MaintenanceDashboardDTO
    observed_signal_count: int = 0
    evidence_gap_count: int = 0
    status: str
    telemetry_collected: bool = False
    monitoring_started: bool = False
    alert_sent: bool = False
    planning_only: bool = True


class PlatformLifecycleMaturityRequestDTO(DirectorModel):
    foundation_request: PlatformLifecycleFoundationRequestDTO
    lifecycle_policy: LifecyclePolicyDTO
    upgrade_policy: UpgradePolicyDTO
    maintenance_policy: MaintenancePolicyDTO


class PlatformLifecycleMaturityReport(DirectorModel):
    dashboard: MaintenanceDashboardDTO
    lifecycle_governance: LifecycleGovernanceReport
    upgrade_governance: UpgradeGovernanceReport
    reliability: PlatformReliabilityReport
    maintenance_policy: MaintenancePolicyReport
    observability: LifecycleObservabilityReport
    lts_compatible: bool = True
    automatic_action_taken: bool = False
    planning_only: bool = True


class PlatformLifecycleMaturityService:
    """Composes human-gated operating-quality evidence for the Lifecycle Plane."""

    def __init__(self, intelligence: LifecycleIntelligenceService | None = None) -> None:
        self._intelligence = intelligence or LifecycleIntelligenceService()

    def report(self, request: PlatformLifecycleMaturityRequestDTO) -> PlatformLifecycleMaturityReport:
        dashboard = self._intelligence.preview(request.foundation_request)
        lifecycle_governance = self._lifecycle_governance(dashboard, request.lifecycle_policy)
        upgrade_governance = self._upgrade_governance(dashboard, request.upgrade_policy)
        maintenance_policy = self._maintenance_policy(dashboard, request.maintenance_policy)
        observability = LifecycleObservabilityReport(
            dashboard=dashboard,
            observed_signal_count=dashboard.health.signal_count,
            evidence_gap_count=dashboard.health.evidence_gap_count,
            status=dashboard.health.health_status,
        )
        reliability = PlatformReliabilityReport(
            dashboard=dashboard,
            metadata_valid=(
                lifecycle_governance.lifecycle_policy_compliant
                and upgrade_governance.upgrade_policy_compliant
                and maintenance_policy.maintenance_policy_compliant
            ),
            reliability_status=(
                "advisory_healthy"
                if dashboard.health.health_status == "healthy"
                else "advisory_attention_required"
            ),
        )
        return PlatformLifecycleMaturityReport(
            dashboard=dashboard,
            lifecycle_governance=lifecycle_governance,
            upgrade_governance=upgrade_governance,
            reliability=reliability,
            maintenance_policy=maintenance_policy,
            observability=observability,
            lts_compatible=dashboard.foundation.lts_compatible,
        )

    @staticmethod
    def _lifecycle_governance(
        dashboard: MaintenanceDashboardDTO, policy: LifecyclePolicyDTO
    ) -> LifecycleGovernanceReport:
        compliant = (
            bool(policy.owner)
            and (not policy.require_lts_compatibility or dashboard.foundation.lts_compatible)
            and (
                not policy.require_lifecycle_evidence
                or dashboard.lifecycle.missing_evidence_count == 0
            )
            and dashboard.foundation.lifecycle.status == "ready"
        )
        return LifecycleGovernanceReport(
            dashboard=dashboard,
            policy=policy,
            lifecycle_policy_compliant=compliant,
        )

    @staticmethod
    def _upgrade_governance(
        dashboard: MaintenanceDashboardDTO, policy: UpgradePolicyDTO
    ) -> UpgradeGovernanceReport:
        plan = dashboard.foundation.upgrade.plan
        lts_valid = not policy.require_lts_compatibility or plan.lts_compatible
        rollback_present = not policy.require_rollback_reference or bool(plan.rollback_reference)
        evidence_present = (
            not policy.require_compatibility_evidence or bool(plan.compatibility_evidence)
        )
        compliant = (
            bool(policy.owner)
            and lts_valid
            and rollback_present
            and evidence_present
            and dashboard.foundation.upgrade.status == "ready"
        )
        return UpgradeGovernanceReport(
            dashboard=dashboard,
            policy=policy,
            upgrade_policy_compliant=compliant,
            lts_compatibility_valid=lts_valid,
            rollback_reference_present=rollback_present,
        )

    @staticmethod
    def _maintenance_policy(
        dashboard: MaintenanceDashboardDTO, policy: MaintenancePolicyDTO
    ) -> MaintenancePolicyReport:
        health_evidence_present = dashboard.health.evidence_gap_count == 0 and dashboard.health.signal_count > 0
        human_decision_present = dashboard.eligible_for_human_maintenance_decision
        compliant = (
            bool(policy.owner)
            and (not policy.require_health_evidence or health_evidence_present)
            and (not policy.require_human_maintenance_decision or human_decision_present)
        )
        return MaintenancePolicyReport(
            dashboard=dashboard,
            policy=policy,
            maintenance_policy_compliant=compliant,
            human_decision_required=policy.require_human_maintenance_decision,
        )
