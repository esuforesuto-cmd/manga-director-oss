"""v5.2 Automation operating-quality diagnostics.

All reports are computed from caller-supplied Automation Foundation metadata.
They do not enforce policy, collect telemetry, recover a runtime, persist a
lifecycle, or advance a workflow. Human approval and the StateMachine retain
their existing authority.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.platform.automation import (
    AutomationEngineFoundation,
    AutomationEngineReport,
    AutomationRequestDTO,
)
from manga_director.platform.automation_intelligence import (
    AutomationDashboardDTO,
    AutomationIntelligenceService,
)
from manga_director.production.director import DirectorModel


class AutomationPolicyDTO(DirectorModel):
    policy_id: str = "automation-policy"
    state_machine_authoritative: bool = True
    one_page_scope_required: bool = True
    human_review_required: bool = True
    automated_execution_prohibited: bool = True
    self_learning_prohibited: bool = True
    policy_enforced: bool = False


class AutomationComplianceDTO(DirectorModel):
    policy_id: str
    template_single_page: bool = False
    template_evidence_valid: bool = False
    human_approval_boundary_declared: bool = False
    rule_safety_boundary_preserved: bool = False
    state_machine_authoritative: bool = True
    compliance_confirmed: bool = False
    enforcement_action_taken: bool = False


class AutomationGovernanceReport(DirectorModel):
    automation: AutomationEngineReport
    policy: AutomationPolicyDTO
    compliance: AutomationComplianceDTO
    human_review_required: bool = True
    automatic_action_taken: bool = False
    planning_only: bool = True


class AutomationGovernanceService:
    """Produces policy evidence without enforcing or modifying automation."""

    def report(self, automation: AutomationEngineReport) -> AutomationGovernanceReport:
        policy = AutomationPolicyDTO()
        template = automation.template.template if automation.template else None
        rule = automation.rule.rule if automation.rule else None
        return AutomationGovernanceReport(
            automation=automation,
            policy=policy,
            compliance=AutomationComplianceDTO(
                policy_id=policy.policy_id,
                template_single_page=bool(template and template.page_count == 1),
                template_evidence_valid=bool(automation.template and automation.template.valid),
                human_approval_boundary_declared=bool(
                    automation.plan and automation.plan.approval_boundary
                ),
                rule_safety_boundary_preserved=bool(
                    rule
                    and rule.human_review_required
                    and not rule.execution_enabled
                    and not rule.self_learning_enabled
                    and not rule.automatic_approval_enabled
                ),
                state_machine_authoritative=automation.state_machine_authoritative,
            ),
        )


class RulePolicyDTO(DirectorModel):
    policy_id: str = "automation-rule-policy"
    explicit_owner_required: bool = True
    evidence_required: bool = True
    human_review_required: bool = True
    execution_prohibited: bool = True
    automatic_approval_prohibited: bool = True
    policy_enforced: bool = False


class RuleComplianceDTO(DirectorModel):
    rule_id: str | None = None
    owner_declared: bool = False
    evidence_complete: bool = False
    safety_boundary_preserved: bool = False
    eligible_for_human_review: bool = False
    compliance_confirmed: bool = False
    rule_changed: bool = False


class RuleGovernanceReport(DirectorModel):
    automation: AutomationEngineReport
    policy: RulePolicyDTO
    compliance: RuleComplianceDTO
    external_audit_performed: bool = False
    planning_only: bool = True


class RuleGovernanceService:
    """Audits the selected explicit rule without learning or editing it."""

    def report(self, automation: AutomationEngineReport) -> RuleGovernanceReport:
        rule_report = automation.rule
        rule = rule_report.rule if rule_report else None
        safe = bool(
            rule
            and rule.human_review_required
            and not rule.execution_enabled
            and not rule.self_learning_enabled
            and not rule.automatic_approval_enabled
        )
        return RuleGovernanceReport(
            automation=automation,
            policy=RulePolicyDTO(),
            compliance=RuleComplianceDTO(
                rule_id=rule.rule_id if rule else None,
                owner_declared=bool(rule and rule.owner),
                evidence_complete=bool(rule_report and not rule_report.missing_evidence),
                safety_boundary_preserved=safe,
                eligible_for_human_review=bool(rule_report and rule_report.eligible),
            ),
        )


class AutomationObservationDTO(DirectorModel):
    observation_id: str
    component: str
    status: Literal["available", "attention_required"]
    evidence_supplied: bool = True
    telemetry_collected: bool = False
    alert_sent: bool = False


class AutomationObservabilityReport(DirectorModel):
    automation: AutomationEngineReport
    observations: tuple[AutomationObservationDTO, ...]
    observation_count: int = Field(default=0, ge=0)
    monitoring_started: bool = False
    report_persisted: bool = False
    planning_only: bool = True


class AutomationObservabilityService:
    """Creates local metadata observations without runtime monitoring."""

    def report(self, automation: AutomationEngineReport) -> AutomationObservabilityReport:
        status: Literal["available", "attention_required"] = (
            "available" if not automation.findings else "attention_required"
        )
        observations = tuple(
            AutomationObservationDTO(
                observation_id=component,
                component=component,
                status=status,
                evidence_supplied=component != "event-bus" or automation.event_bus.event_count > 0,
            )
            for component in ("automation-engine", "rule-engine", "event-bus", "workflow")
        )
        return AutomationObservabilityReport(
            automation=automation,
            observations=observations,
            observation_count=len(observations),
        )


class AutomationReliabilityComponentDTO(DirectorModel):
    component_id: str
    status: Literal["metadata_valid", "metadata_attention_required"]
    health_check_performed: bool = False
    recovery_attempted: bool = False
    automatic_recovery_taken: bool = False


class AutomationReliabilityReport(DirectorModel):
    observability: AutomationObservabilityReport
    components: tuple[AutomationReliabilityComponentDTO, ...]
    component_count: int = Field(default=0, ge=0)
    runtime_reconfigured: bool = False
    planning_only: bool = True


class AutomationReliabilityService:
    """Reports metadata confidence only; it cannot repair automation."""

    def report(self, observability: AutomationObservabilityReport) -> AutomationReliabilityReport:
        status: Literal["metadata_valid", "metadata_attention_required"] = (
            "metadata_valid"
            if not observability.automation.findings
            else "metadata_attention_required"
        )
        components = tuple(
            AutomationReliabilityComponentDTO(component_id=item.component, status=status)
            for item in observability.observations
        )
        return AutomationReliabilityReport(
            observability=observability,
            components=components,
            component_count=len(components),
        )


class AutomationLifecycleDTO(DirectorModel):
    automation_id: str | None = None
    stage: Literal["advisory"] = "advisory"
    human_approval_boundary_declared: bool = False
    lifecycle_transitioned: bool = False
    lifecycle_persisted: bool = False


class AutomationLifecycleReport(DirectorModel):
    automation: AutomationEngineReport
    lifecycle: AutomationLifecycleDTO
    retention_enforced: bool = False
    recovery_attempted: bool = False
    planning_only: bool = True


class AutomationLifecycleManagementService:
    """Describes advisory lifecycle metadata without changing lifecycle state."""

    def report(self, automation: AutomationEngineReport) -> AutomationLifecycleReport:
        plan = automation.plan
        return AutomationLifecycleReport(
            automation=automation,
            lifecycle=AutomationLifecycleDTO(
                automation_id=plan.automation_id if plan else None,
                human_approval_boundary_declared=bool(plan and plan.approval_boundary),
            ),
        )


class AutomationPlatformMaturityReport(DirectorModel):
    automation: AutomationEngineReport
    dashboard: AutomationDashboardDTO
    governance: AutomationGovernanceReport
    rule_governance: RuleGovernanceReport
    observability: AutomationObservabilityReport
    reliability: AutomationReliabilityReport
    lifecycle: AutomationLifecycleReport
    lts_compatible: bool = True
    automatic_action_taken: bool = False
    planning_only: bool = True


class AutomationPlatformMaturityService:
    """Composes v5.2 operating-quality evidence without running automation."""

    def __init__(
        self,
        engine: AutomationEngineFoundation | None = None,
        intelligence: AutomationIntelligenceService | None = None,
        governance: AutomationGovernanceService | None = None,
        rule_governance: RuleGovernanceService | None = None,
        observability: AutomationObservabilityService | None = None,
        reliability: AutomationReliabilityService | None = None,
        lifecycle: AutomationLifecycleManagementService | None = None,
    ) -> None:
        self._engine = engine or AutomationEngineFoundation()
        self._intelligence = intelligence or AutomationIntelligenceService(self._engine)
        self._governance = governance or AutomationGovernanceService()
        self._rule_governance = rule_governance or RuleGovernanceService()
        self._observability = observability or AutomationObservabilityService()
        self._reliability = reliability or AutomationReliabilityService()
        self._lifecycle = lifecycle or AutomationLifecycleManagementService()

    def report(self, request: AutomationRequestDTO) -> AutomationPlatformMaturityReport:
        automation = self._engine.preview(request)
        observability = self._observability.report(automation)
        return AutomationPlatformMaturityReport(
            automation=automation,
            dashboard=self._intelligence.preview(request),
            governance=self._governance.report(automation),
            rule_governance=self._rule_governance.report(automation),
            observability=observability,
            reliability=self._reliability.report(observability),
            lifecycle=self._lifecycle.report(automation),
        )
