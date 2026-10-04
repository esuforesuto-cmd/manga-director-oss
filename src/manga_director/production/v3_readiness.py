"""v3 Production-readiness validation and dashboard DTOs with no execution authority."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.v3_collaboration import CollaborationPlanningService
from manga_director.production.v3_foundation import DirectorPlanningService
from manga_director.workflow.contracts import WorkflowContext


class DirectorSessionValidation(DirectorModel):
    valid: bool
    page_scope: Literal["one_page"] = "one_page"
    findings: tuple[str, ...] = ()
    execution_performed: bool = False


class PlanningIntegrityValidation(DirectorModel):
    valid: bool
    state_machine_derived: bool = True
    next_command: str | None = None
    workflow_mutated: bool = False


class DecisionConsistencyAnalysis(DirectorModel):
    consistent: bool
    session_command: str | None = None
    intelligence_command: str | None = None
    findings: tuple[str, ...] = ()


class CreativeStrategyValidation(DirectorModel):
    valid: bool
    storyboard_guard_visible: bool
    strategy_executed: bool = False
    findings: tuple[str, ...] = ()


class ExecutionReadinessReport(DirectorModel):
    ready_for_human_decision: bool
    recommended_command: str | None = None
    blockers: tuple[str, ...] = ()
    execution_enabled: bool = False


class DirectorReliabilitySummary(DirectorModel):
    session: DirectorSessionValidation
    planning: PlanningIntegrityValidation
    consistency: DecisionConsistencyAnalysis
    creative_strategy: CreativeStrategyValidation
    readiness: ExecutionReadinessReport
    reliable: bool
    automatic_action_taken: bool = False


class CreativePolicyValidation(DirectorModel):
    valid: bool
    policy: Literal["existing_workflow_guards"] = "existing_workflow_guards"
    execution_enabled: bool = False


class CreativeStandardReport(DirectorModel):
    standards: tuple[str, ...] = ("storyboard evidence", "quality review", "human approval")
    compliant: bool
    findings: tuple[str, ...] = ()


class CreativeGovernanceSummary(DirectorModel):
    policy: CreativePolicyValidation
    standards: CreativeStandardReport
    review_pipeline_diagnostic: bool = True
    governance_only: bool = True


class PlanningComplianceReport(DirectorModel):
    compliant: bool
    required_checkpoints: tuple[str, ...] = ()
    workflow_changed: bool = False


class CreativeAuditReport(DirectorModel):
    findings: tuple[str, ...] = ()
    audit_only: bool = True
    persistence_mutated: bool = False


class CreativeGovernanceReport(DirectorModel):
    summary: CreativeGovernanceSummary
    compliance: PlanningComplianceReport
    audit: CreativeAuditReport
    automatic_action_taken: bool = False


class KnowledgeIntegrityValidation(DirectorModel):
    valid: bool
    repository_read_only: bool = True
    findings: tuple[str, ...] = ()


class KnowledgeCoverageReport(DirectorModel):
    references: int = Field(ge=0)
    relationships: int = Field(ge=0)
    coverage: Literal["empty", "available"]


class KnowledgeLifecycleReport(DirectorModel):
    source: Literal["repository_projection"] = "repository_projection"
    persistence_mutated: bool = False
    retention_managed: bool = False


class KnowledgeQualityScore(DirectorModel):
    score: int = Field(ge=0, le=100)
    rationale: str


class KnowledgeGovernanceSummary(DirectorModel):
    integrity: KnowledgeIntegrityValidation
    coverage: KnowledgeCoverageReport
    lifecycle: KnowledgeLifecycleReport
    quality: KnowledgeQualityScore
    governance_only: bool = True


class KnowledgeRiskReport(DirectorModel):
    level: Literal["low", "medium"]
    risks: tuple[str, ...] = ()
    automatic_remediation: bool = False


class KnowledgeIntegrityReport(DirectorModel):
    governance: KnowledgeGovernanceSummary
    risk: KnowledgeRiskReport
    persistence_mutated: bool = False


class WorkflowDeploymentReadiness(DirectorModel):
    ready: bool
    one_page_scope: bool = True
    state_machine_unchanged: bool = True
    deployment_performed: bool = False


class DirectorDeploymentReadiness(DirectorModel):
    ready: bool
    execution_authority_added: bool = False
    deployment_performed: bool = False


class KnowledgeDeploymentReadiness(DirectorModel):
    ready: bool
    repository_interface_preserved: bool = True
    deployment_performed: bool = False


class ConfigurationValidation(DirectorModel):
    valid: bool
    configured_keys: tuple[str, ...] = ()
    values_exposed: bool = False


class OperationalReadinessSummary(DirectorModel):
    ready_for_review: bool
    required_checks: tuple[str, ...] = ()
    operation_started: bool = False


class ProductionReadinessReport(DirectorModel):
    workflow: WorkflowDeploymentReadiness
    director: DirectorDeploymentReadiness
    knowledge: KnowledgeDeploymentReadiness
    configuration: ConfigurationValidation
    operations: OperationalReadinessSummary
    deployment_performed: bool = False


class DirectorExecutiveDTO(DirectorModel):
    report: DirectorReliabilitySummary
    automatic_action_taken: bool = False


class CreativeExecutiveDTO(DirectorModel):
    report: CreativeGovernanceReport
    automatic_action_taken: bool = False


class KnowledgeExecutiveDTO(DirectorModel):
    report: KnowledgeIntegrityReport
    automatic_action_taken: bool = False


class ProductionExecutiveDTO(DirectorModel):
    report: ProductionReadinessReport
    deployment_performed: bool = False


class ReleaseReadinessDTO(DirectorModel):
    director: DirectorExecutiveDTO
    creative: CreativeExecutiveDTO
    knowledge: KnowledgeExecutiveDTO
    production: ProductionExecutiveDTO
    release_authorized: bool = False
    automatic_release: bool = False


class V3ReadinessService:
    """Validate v3 DTO evidence without changing Core or starting an operation."""

    def __init__(
        self, foundation: DirectorPlanningService, collaboration: CollaborationPlanningService
    ) -> None:
        self._foundation = foundation
        self._collaboration = collaboration

    def director_reliability(self, context: WorkflowContext) -> DirectorReliabilitySummary:
        session = self._foundation.director_session(context)
        intelligence = self._collaboration.director_intelligence(context)
        creative = self._foundation.creative_planning(context)
        consistent = session.summary.recommended_command == intelligence.decision.next_command
        storyboard_visible = creative.panels.storyboard_persisted or context.state is not PageState.PROMPT_BUILT
        blockers = () if storyboard_visible else ("Persisted storyboard evidence is required before generation.",)
        return DirectorReliabilitySummary(
            session=DirectorSessionValidation(valid=session.session.planning_context.page_scope == "one_page"),
            planning=PlanningIntegrityValidation(
                valid=session.summary.recommended_command == session.session.execution_context.recommended_command,
                next_command=session.summary.recommended_command,
            ),
            consistency=DecisionConsistencyAnalysis(
                consistent=consistent,
                session_command=session.summary.recommended_command,
                intelligence_command=intelligence.decision.next_command,
            ),
            creative_strategy=CreativeStrategyValidation(
                valid=not creative.page.execution_enabled,
                storyboard_guard_visible=storyboard_visible,
                findings=blockers,
            ),
            readiness=ExecutionReadinessReport(
                ready_for_human_decision=session.summary.ready and not blockers,
                recommended_command=session.summary.recommended_command,
                blockers=blockers,
            ),
            reliable=consistent and not creative.page.execution_enabled,
        )

    def creative_governance(self, context: WorkflowContext) -> CreativeGovernanceReport:
        creative = self._foundation.creative_planning(context)
        review = self._collaboration.review_pipeline(context)
        storyboard_guard = creative.panels.storyboard_persisted or context.state is not PageState.PROMPT_BUILT
        findings = () if storyboard_guard else ("Storyboard guard requires persisted evidence.",)
        return CreativeGovernanceReport(
            summary=CreativeGovernanceSummary(
                policy=CreativePolicyValidation(valid=True),
                standards=CreativeStandardReport(compliant=storyboard_guard, findings=findings),
            ),
            compliance=PlanningComplianceReport(
                compliant=not creative.page.execution_enabled,
                required_checkpoints=("Storyboard", "QualityReview", "HumanApproval"),
            ),
            audit=CreativeAuditReport(findings=review.summary.findings),
        )

    def knowledge_integrity(self, context: WorkflowContext | None = None) -> KnowledgeIntegrityReport:
        knowledge = self._collaboration.creative_knowledge(context)
        references = sum(
            len(topic.references)
            for topic in (
                knowledge.character,
                knowledge.world,
                knowledge.story,
                knowledge.scene,
                knowledge.asset,
            )
        )
        coverage: Literal["empty", "available"] = "available" if references else "empty"
        score = 100 if knowledge.repository_read_only else 0
        risks = () if coverage == "available" else ("Knowledge coverage is currently limited to available repository projections.",)
        return KnowledgeIntegrityReport(
            governance=KnowledgeGovernanceSummary(
                integrity=KnowledgeIntegrityValidation(valid=knowledge.repository_read_only),
                coverage=KnowledgeCoverageReport(
                    references=references,
                    relationships=knowledge.relationships.relationship_count,
                    coverage=coverage,
                ),
                lifecycle=KnowledgeLifecycleReport(),
                quality=KnowledgeQualityScore(
                    score=score,
                    rationale="Repository-derived identifiers and metadata keys are redacted and read-only.",
                ),
            ),
            risk=KnowledgeRiskReport(level="medium" if risks else "low", risks=risks),
        )

    def production_readiness(
        self, context: WorkflowContext, configuration: Mapping[str, Any] | None = None
    ) -> ProductionReadinessReport:
        director = self.director_reliability(context)
        knowledge = self.knowledge_integrity(context)
        configured_keys = tuple(sorted(str(key) for key in (configuration or {})))
        return ProductionReadinessReport(
            workflow=WorkflowDeploymentReadiness(ready=director.reliable),
            director=DirectorDeploymentReadiness(ready=director.reliable),
            knowledge=KnowledgeDeploymentReadiness(
                ready=knowledge.governance.integrity.valid
            ),
            configuration=ConfigurationValidation(valid=True, configured_keys=configured_keys),
            operations=OperationalReadinessSummary(
                ready_for_review=director.reliable and knowledge.governance.integrity.valid,
                required_checks=("human review", "workflow guards", "repository projection"),
            ),
        )

    def director_executive(self, context: WorkflowContext) -> DirectorExecutiveDTO:
        return DirectorExecutiveDTO(report=self.director_reliability(context))

    def creative_executive(self, context: WorkflowContext) -> CreativeExecutiveDTO:
        return CreativeExecutiveDTO(report=self.creative_governance(context))

    def knowledge_executive(self, context: WorkflowContext | None = None) -> KnowledgeExecutiveDTO:
        return KnowledgeExecutiveDTO(report=self.knowledge_integrity(context))

    def production_executive(
        self, context: WorkflowContext, configuration: Mapping[str, Any] | None = None
    ) -> ProductionExecutiveDTO:
        return ProductionExecutiveDTO(report=self.production_readiness(context, configuration))

    def release_dashboard(
        self, context: WorkflowContext, configuration: Mapping[str, Any] | None = None
    ) -> ReleaseReadinessDTO:
        return ReleaseReadinessDTO(
            director=self.director_executive(context),
            creative=self.creative_executive(context),
            knowledge=self.knowledge_executive(context),
            production=self.production_executive(context, configuration),
        )
