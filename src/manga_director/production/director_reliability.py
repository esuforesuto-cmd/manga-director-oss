"""Read-only AI Director reliability, Knowledge governance, and readiness DTOs.

This application-layer service composes the v2.7 planning services.  It is
deliberately unable to execute a workflow step, invoke an Agent or Provider,
or write through a Repository port.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director._version import __version__
from manga_director.production.director import (
    DecisionTrace,
    DirectorFoundationService,
    DirectorModel,
)
from manga_director.production.intelligence import KnowledgeIntelligenceService
from manga_director.workflow.contracts import WorkflowContext


class DirectorIntegrityAnalysis(DirectorModel):
    """Verify that an advisory plan remains within the one-page boundary."""

    valid: bool
    page_scope: Literal["one_page"] = "one_page"
    state_machine_derived: bool = True
    findings: tuple[str, ...] = ()


class DirectorConsistencyValidation(DirectorModel):
    """Verify that a plan and its readiness decision agree."""

    valid: bool
    strategy_command: str | None = None
    readiness_command: str | None = None
    messages: tuple[str, ...] = ()


class DecisionTraceValidation(DirectorModel):
    """Bounded validation of a public decision trace, never hidden reasoning."""

    valid: bool
    assumptions_bounded: bool
    evidence_bounded: bool
    side_effects: Literal["none"] = "none"
    messages: tuple[str, ...] = ()


class PlanningReliabilityReport(DirectorModel):
    """Integrity, consistency, trace, and readiness evidence for one Page."""

    integrity: DirectorIntegrityAnalysis
    consistency: DirectorConsistencyValidation
    decision_trace: DecisionTraceValidation
    ready: bool
    next_command: str | None = None
    execution_performed: bool = False


class DirectorReliabilitySummary(DirectorModel):
    """Compact reliability evidence suitable for a transport adapter."""

    reliable: bool
    ready: bool
    next_command: str | None = None
    messages: tuple[str, ...] = ()


class KnowledgePolicyValidation(DirectorModel):
    """Repository-port policy evidence for knowledge projections."""

    valid: bool
    policy: Literal["repository_derived_redacted"] = "repository_derived_redacted"
    messages: tuple[str, ...] = ()


class KnowledgeIntegrityReport(DirectorModel):
    """Integrity result for repository-derived, redacted knowledge entries."""

    valid: bool
    indexed_projects: int = Field(ge=0)
    findings: tuple[str, ...] = ()


class KnowledgeLifecycleSummary(DirectorModel):
    """Lifecycle boundaries of the read-only knowledge projection."""

    source: Literal["repository"] = "repository"
    persistence_mutated: bool = False
    retention_managed: bool = False
    messages: tuple[str, ...] = ()


class KnowledgeQualityScore(DirectorModel):
    """Deterministic coverage score, not a semantic correctness claim."""

    score: int = Field(ge=0, le=100)
    rationale: str


class KnowledgeRiskSummary(DirectorModel):
    """Advisory governance risk with no automatic remediation."""

    level: Literal["low", "medium"]
    risks: tuple[str, ...] = ()
    mitigations: tuple[str, ...] = ()


class KnowledgeGovernanceReport(DirectorModel):
    """Policy, integrity, lifecycle, quality, and risk evidence."""

    policy: KnowledgePolicyValidation
    integrity: KnowledgeIntegrityReport
    lifecycle: KnowledgeLifecycleSummary
    quality: KnowledgeQualityScore
    risk: KnowledgeRiskSummary
    governance_only: bool = True


class EnterpriseAIReadinessReport(DirectorModel):
    """Deployment-readiness checklist for AI planning facilities only."""

    ready: bool
    knowledge_deployment_ready: bool
    workflow_deployment_ready: bool
    configuration_ready: bool
    operational_ready: bool
    governance_ready: bool
    messages: tuple[str, ...] = ()
    deployment_performed: bool = False


class AIWorkflowDiagnostics(DirectorModel):
    """Transport-neutral diagnostics assembled from bounded public DTOs."""

    director: dict[str, object]
    knowledge: dict[str, object]
    planning: dict[str, object]
    workflow: dict[str, object]
    architecture: dict[str, object]
    diagnostics_only: bool = True


class AIWorkflowExecutiveSummary(DirectorModel):
    """High-level summary safe for CLI, FastAPI, and MCP delivery."""

    reliable: bool
    knowledge_quality: int = Field(ge=0, le=100)
    enterprise_ready: bool
    next_command: str | None = None
    automatic_action_taken: bool = False


class DirectorDashboard(DirectorModel):
    """Dashboard DTO for Director reliability; it has no presentation behavior."""

    reliable: bool
    ready: bool
    next_command: str | None = None


class KnowledgeDashboard(DirectorModel):
    """Dashboard DTO for knowledge governance evidence."""

    quality_score: int = Field(ge=0, le=100)
    governance_valid: bool
    risk_level: Literal["low", "medium"]


class WorkflowDashboard(DirectorModel):
    """Dashboard DTO for the current one-page workflow advisory state."""

    state: str
    next_command: str | None = None
    execution_performed: bool = False


class EnterpriseAIDashboard(DirectorModel):
    """Dashboard DTO for enterprise AI readiness."""

    ready: bool
    ready_areas: int = Field(ge=0)
    total_areas: int = Field(ge=0)


class DirectorReleaseDashboard(DirectorModel):
    """Release-facing evidence with no build, tag, or publish capability."""

    version: str = __version__
    release_ready: bool
    automatic_release: bool = False


class DirectorExecutiveDashboard(DirectorModel):
    """Composite dashboard DTO for all v2.7 reliability evidence."""

    director: DirectorDashboard
    knowledge: KnowledgeDashboard
    workflow: WorkflowDashboard
    enterprise: EnterpriseAIDashboard
    release: DirectorReleaseDashboard


class DirectorReliabilityService:
    """Read-only v2.7 reliability facade composed from application services."""

    def __init__(
        self,
        foundation: DirectorFoundationService,
        intelligence: KnowledgeIntelligenceService,
    ) -> None:
        self._foundation = foundation
        self._intelligence = intelligence

    def director_reliability(self, context: WorkflowContext) -> PlanningReliabilityReport:
        """Validate one planning result without dispatching a workflow command."""

        plan = self._foundation.director_plan(context)
        integrity = DirectorIntegrityAnalysis(
            valid=plan.dependencies.current_state is context.state,
            findings=()
            if plan.dependencies.current_state is context.state
            else ("Planning dependency state differs from the supplied context.",),
        )
        consistency = DirectorConsistencyValidation(
            valid=plan.strategy.command == plan.readiness.next_command,
            strategy_command=plan.strategy.command,
            readiness_command=plan.readiness.next_command,
            messages=("Strategy and readiness use the same StateMachine recommendation.",),
        )
        trace = _validate_trace(plan.trace)
        ready = integrity.valid and consistency.valid and trace.valid and plan.readiness.ready
        return PlanningReliabilityReport(
            integrity=integrity,
            consistency=consistency,
            decision_trace=trace,
            ready=ready,
            next_command=plan.readiness.next_command if ready else None,
        )

    def director_summary(self, context: WorkflowContext) -> DirectorReliabilitySummary:
        report = self.director_reliability(context)
        return DirectorReliabilitySummary(
            reliable=report.integrity.valid
            and report.consistency.valid
            and report.decision_trace.valid,
            ready=report.ready,
            next_command=report.next_command,
            messages=("This is advisory evidence; WorkflowEngine remains the only executor.",),
        )

    def knowledge_governance(self) -> KnowledgeGovernanceReport:
        intelligence = self._intelligence.knowledge_intelligence()
        entries = intelligence.knowledge.snapshot.entries
        policy = KnowledgePolicyValidation(
            valid=intelligence.knowledge.snapshot.mutated_repository is False,
            messages=("Knowledge is redacted and derived through the Repository port.",),
        )
        integrity = KnowledgeIntegrityReport(
            valid=intelligence.consistency.consistent
            and all(entry.project_id and entry.title for entry in entries),
            indexed_projects=len(entries),
            findings=intelligence.consistency.findings,
        )
        quality = KnowledgeQualityScore(
            score=0 if not entries else 100 if intelligence.coverage.coverage == "available" else 60,
            rationale="Score reflects deterministic local index coverage only.",
        )
        risks = () if integrity.valid and quality.score >= 60 else ("Knowledge coverage requires review.",)
        return KnowledgeGovernanceReport(
            policy=policy,
            integrity=integrity,
            lifecycle=KnowledgeLifecycleSummary(
                messages=("No index, retention policy, or repository mutation is created.",)
            ),
            quality=quality,
            risk=KnowledgeRiskSummary(
                level="low" if not risks else "medium",
                risks=risks,
                mitigations=("Review repository metadata ownership before increasing knowledge coverage.",),
            ),
        )

    def enterprise_ai_readiness(self, context: WorkflowContext) -> EnterpriseAIReadinessReport:
        reliability = self.director_reliability(context)
        governance = self.knowledge_governance()
        knowledge_ready = governance.policy.valid and governance.integrity.valid
        workflow_ready = reliability.integrity.valid and reliability.consistency.valid
        configuration_ready = True
        operational_ready = reliability.decision_trace.valid
        governance_ready = governance.risk.level == "low"
        ready = all(
            (knowledge_ready, workflow_ready, configuration_ready, operational_ready, governance_ready)
        )
        return EnterpriseAIReadinessReport(
            ready=ready,
            knowledge_deployment_ready=knowledge_ready,
            workflow_deployment_ready=workflow_ready,
            configuration_ready=configuration_ready,
            operational_ready=operational_ready,
            governance_ready=governance_ready,
            messages=("Checklist only; it does not deploy, resume, or execute a workflow.",),
        )

    def diagnostics(self, context: WorkflowContext) -> AIWorkflowDiagnostics:
        reliability = self.director_reliability(context)
        governance = self.knowledge_governance()
        plan = self._foundation.director_plan(context)
        optimization = self._intelligence.workflow_optimization(context)
        return AIWorkflowDiagnostics(
            director=self.director_summary(context).model_dump(mode="json"),
            knowledge=governance.model_dump(mode="json"),
            planning={
                "decision": plan.trace.decision,
                "next_command": plan.readiness.next_command,
                "ready": reliability.ready,
            },
            workflow={
                "state": context.state.value,
                "critical_path": optimization.critical_path,
                "workflow_modified": optimization.workflow_modified,
            },
            architecture={
                "workflow_engine_modified": False,
                "repository_interface_modified": False,
                "execution_boundary": "WorkflowEngine only",
            },
        )

    def executive_summary(self, context: WorkflowContext) -> AIWorkflowExecutiveSummary:
        reliability = self.director_reliability(context)
        governance = self.knowledge_governance()
        readiness = self.enterprise_ai_readiness(context)
        return AIWorkflowExecutiveSummary(
            reliable=reliability.integrity.valid
            and reliability.consistency.valid
            and reliability.decision_trace.valid,
            knowledge_quality=governance.quality.score,
            enterprise_ready=readiness.ready,
            next_command=reliability.next_command,
        )

    def dashboard(self, context: WorkflowContext) -> DirectorExecutiveDashboard:
        reliability = self.director_reliability(context)
        governance = self.knowledge_governance()
        readiness = self.enterprise_ai_readiness(context)
        ready_areas = sum(
            (
                readiness.knowledge_deployment_ready,
                readiness.workflow_deployment_ready,
                readiness.configuration_ready,
                readiness.operational_ready,
                readiness.governance_ready,
            )
        )
        return DirectorExecutiveDashboard(
            director=DirectorDashboard(
                reliable=reliability.integrity.valid
                and reliability.consistency.valid
                and reliability.decision_trace.valid,
                ready=reliability.ready,
                next_command=reliability.next_command,
            ),
            knowledge=KnowledgeDashboard(
                quality_score=governance.quality.score,
                governance_valid=governance.policy.valid and governance.integrity.valid,
                risk_level=governance.risk.level,
            ),
            workflow=WorkflowDashboard(state=context.state.value, next_command=reliability.next_command),
            enterprise=EnterpriseAIDashboard(
                ready=readiness.ready, ready_areas=ready_areas, total_areas=5
            ),
            release=DirectorReleaseDashboard(release_ready=readiness.ready),
        )


def _validate_trace(trace: DecisionTrace) -> DecisionTraceValidation:
    assumptions_bounded = bool(trace.assumptions) and len(trace.assumptions) <= 4
    evidence_bounded = len(trace.evidence) <= 4
    valid = assumptions_bounded and evidence_bounded and trace.side_effects == "none"
    return DecisionTraceValidation(
        valid=valid,
        assumptions_bounded=assumptions_bounded,
        evidence_bounded=evidence_bounded,
        messages=("Decision trace contains public policy evidence only.",),
    )
