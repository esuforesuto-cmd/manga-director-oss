"""Read-only Knowledge Intelligence and AI Director analysis DTOs."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import (
    DirectorFoundationService,
    DirectorModel,
    KnowledgeEntry,
    KnowledgeReport,
    OrchestrationSummary,
)
from manga_director.workflow.contracts import WorkflowContext


class KnowledgeRelationshipGraph(DirectorModel):
    nodes: tuple[str, ...] = ()
    edges: tuple[tuple[str, str], ...] = ()
    analysis_only: bool = True


class KnowledgeCoverageAnalysis(DirectorModel):
    indexed_projects: int = Field(ge=0)
    metadata_key_count: int = Field(ge=0)
    coverage: Literal["empty", "partial", "available"]


class KnowledgeConsistencyReport(DirectorModel):
    consistent: bool
    findings: tuple[str, ...] = ()


class KnowledgeIntelligenceReport(DirectorModel):
    knowledge: KnowledgeReport
    relationships: KnowledgeRelationshipGraph
    coverage: KnowledgeCoverageAnalysis
    consistency: KnowledgeConsistencyReport
    recommendation: str


class PlanningAlternative(DirectorModel):
    name: str
    command: str | None = None
    executable: bool = False
    rationale: str


class ExecutionRiskAnalysis(DirectorModel):
    level: Literal["low", "medium"]
    factors: tuple[str, ...] = ()
    execution_performed: bool = False


class DirectorAnalysisReport(DirectorModel):
    alternatives: tuple[PlanningAlternative, ...] = ()
    selected_strategy: str
    comparison: str
    risk: ExecutionRiskAnalysis
    explanation: str


class WorkflowOptimizationReport(DirectorModel):
    critical_path: tuple[str, ...] = ()
    dependency_optimization: tuple[str, ...] = ()
    efficiency: Literal["bounded"] = "bounded"
    recommendation: str
    workflow_modified: bool = False


class EnterpriseKnowledgeReport(DirectorModel):
    inventory: int = Field(ge=0)
    health: bool
    governance: tuple[str, ...] = ()
    audit_only: bool = True


class OptimizationDashboard(DirectorModel):
    knowledge: KnowledgeIntelligenceReport
    director: DirectorAnalysisReport
    workflow: WorkflowOptimizationReport
    enterprise: EnterpriseKnowledgeReport
    automatic_action_taken: bool = False


class KnowledgeIntelligenceService:
    """Compose comparisons and recommendations from the existing read-only facade."""

    def __init__(self, foundation: DirectorFoundationService) -> None:
        self._foundation = foundation

    def knowledge_intelligence(self) -> KnowledgeIntelligenceReport:
        report = self._foundation.knowledge_report()
        entries = report.snapshot.entries
        keys: dict[str, list[str]] = {}
        for entry in entries:
            for key in entry.metadata_keys:
                keys.setdefault(key, []).append(entry.project_id)
        edges = tuple((project, key) for key, projects in sorted(keys.items()) for project in projects)
        coverage: Literal["empty", "partial", "available"] = (
            "empty" if not entries else "available" if keys else "partial"
        )
        return KnowledgeIntelligenceReport(
            knowledge=report,
            relationships=KnowledgeRelationshipGraph(nodes=tuple(entry.project_id for entry in entries) + tuple(sorted(keys)), edges=edges),
            coverage=KnowledgeCoverageAnalysis(indexed_projects=len(entries), metadata_key_count=len(keys), coverage=coverage),
            consistency=KnowledgeConsistencyReport(consistent=True, findings=()),
            recommendation="Use repository-derived knowledge as advisory evidence; review ownership before expanding coverage.",
        )

    def similarity(self, query: str) -> tuple[KnowledgeEntry, ...]:
        """Return deterministic key/title similarity through the existing Knowledge service."""
        return self._foundation.knowledge_search(query).matches

    def director_analysis(self, context: WorkflowContext) -> DirectorAnalysisReport:
        plan = self._foundation.director_plan(context)
        command = plan.strategy.command
        alternatives = (
            PlanningAlternative(name="state_machine_next_step", command=command, rationale=plan.strategy.rationale),
            PlanningAlternative(name="human_review", rationale="Review the decision trace before any explicit workflow command."),
        )
        factors = ("Human approval remains explicit.",) if plan.strategy.target_state and plan.strategy.target_state.value == "Approved" else ()
        return DirectorAnalysisReport(
            alternatives=alternatives,
            selected_strategy="state_machine_next_step",
            comparison="Alternatives are advisory; no strategy is executed.",
            risk=ExecutionRiskAnalysis(level="medium" if factors else "low", factors=factors),
            explanation=plan.trace.decision,
        )

    def workflow_optimization(self, context: WorkflowContext) -> WorkflowOptimizationReport:
        orchestration: OrchestrationSummary = self._foundation.orchestration(context)
        commands = orchestration.preview.commands
        return WorkflowOptimizationReport(
            critical_path=commands,
            dependency_optimization=("Preserve StateMachine order; do not skip prerequisites.",),
            recommendation="Use the next legal step only after review; this report does not modify the workflow.",
        )

    def enterprise_knowledge(self) -> EnterpriseKnowledgeReport:
        report = self._foundation.knowledge_report()
        return EnterpriseKnowledgeReport(
            inventory=report.summary.project_count,
            health=report.health.healthy,
            governance=("Repository port only", "Redacted metadata values", "No automatic mutation"),
        )

    def dashboard(self, context: WorkflowContext) -> OptimizationDashboard:
        return OptimizationDashboard(
            knowledge=self.knowledge_intelligence(),
            director=self.director_analysis(context),
            workflow=self.workflow_optimization(context),
            enterprise=self.enterprise_knowledge(),
        )
