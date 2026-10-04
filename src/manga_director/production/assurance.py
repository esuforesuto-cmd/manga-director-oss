"""Read-only AI workflow reliability, Provider governance, and readiness DTOs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from manga_director._version import __version__
from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.cli.config import AppConfig, configuration_governance
from manga_director.production.analytics import (
    ProviderOptimizationReport,
    ProviderOptimizer,
    WorkflowDependencyAnalyzer,
)
from manga_director.production.planning import PlanningService
from manga_director.production.quality import RepositoryMaintenance
from manga_director.workflow.contracts import WorkflowContext


class AssuranceModel(BaseModel):
    """Immutable, transport-neutral DTO base for assurance reports."""

    model_config = ConfigDict(frozen=True)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown(_title(self.__class__.__name__), self.model_dump(mode="json"))


class WorkflowIntegrityAnalysis(AssuranceModel):
    """Evidence that a single context has the artifact and history needed for review."""

    valid: bool
    current_state: str
    history_consistent: bool
    required_artifacts_present: bool
    findings: tuple[str, ...] = ()


class WorkflowValidationReport(AssuranceModel):
    """A read-only validation result derived from the existing StateMachine plan."""

    valid: bool
    next_command: str | None = None
    approved_terminal: bool
    messages: tuple[str, ...] = ()


class WorkflowConsistencyAnalysis(AssuranceModel):
    """State/history alignment evidence without loading, saving, or resuming work."""

    consistent: bool
    observed_history_steps: int = Field(ge=0)
    expected_completed_steps: int = Field(ge=0)
    messages: tuple[str, ...] = ()


class WorkflowRiskAssessment(AssuranceModel):
    """Advisory workflow risk categorization; it never blocks execution itself."""

    level: Literal["low", "medium", "high"]
    risks: tuple[str, ...] = ()
    mitigations: tuple[str, ...] = ()


class ExecutionReadinessReport(AssuranceModel):
    """An advisory readiness decision; WorkflowEngine remains the executor."""

    ready: bool
    next_command: str | None = None
    reasons: tuple[str, ...] = ()
    execution_performed: bool = False


class WorkflowReliabilityReport(AssuranceModel):
    """Workflow integrity, validation, consistency, risk, and readiness evidence."""

    integrity: WorkflowIntegrityAnalysis
    validation: WorkflowValidationReport
    consistency: WorkflowConsistencyAnalysis
    risk: WorkflowRiskAssessment
    readiness: ExecutionReadinessReport
    analysis_only: bool = True


class ProviderPolicyValidation(AssuranceModel):
    """Provider policy validation that leaves Factory registration untouched."""

    valid: bool
    default_provider: str
    registered_providers: tuple[str, ...] = ()
    allowed_providers: tuple[str, ...] = ()
    messages: tuple[str, ...] = ()


class ProviderCapabilityAudit(AssuranceModel):
    """Capability coverage audit over registered Provider metadata."""

    capabilities: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    providers_with_capabilities: int = Field(ge=0)
    valid: bool


class ProviderLifecycleSummary(AssuranceModel):
    """Local lifecycle summary; no remote probe or model request is made."""

    registered: int = Field(ge=0)
    healthy: int = Field(ge=0)
    states: dict[str, int] = Field(default_factory=dict)
    network_probes: bool = False


class ProviderCompatibilityReport(AssuranceModel):
    """Protocol-preserving compatibility evidence for the configured default."""

    compatible: bool
    default_provider: str
    recommendation: str | None = None
    messages: tuple[str, ...] = ()


class ProviderRiskSummary(AssuranceModel):
    """Metadata-only risk assessment for Provider operations."""

    level: Literal["low", "medium", "high"]
    risks: tuple[str, ...] = ()
    mitigations: tuple[str, ...] = ()


class ProviderGovernanceReport(AssuranceModel):
    """Provider policy, capability, lifecycle, compatibility, and risk evidence."""

    policy: ProviderPolicyValidation
    capabilities: ProviderCapabilityAudit
    lifecycle: ProviderLifecycleSummary
    compatibility: ProviderCompatibilityReport
    risk: ProviderRiskSummary
    optimization: ProviderOptimizationReport
    governance_only: bool = True


class ReadinessArea(AssuranceModel):
    """One enterprise readiness area with non-automating guidance."""

    name: str
    ready: bool
    guidance: str


class EnterpriseReadinessReport(AssuranceModel):
    """Deployment, operations, maintenance, configuration, and recovery readiness."""

    ready: bool
    deployment: ReadinessArea
    operations: ReadinessArea
    maintenance: ReadinessArea
    configuration: ReadinessArea
    recovery: ReadinessArea
    workflow: ReadinessArea


class WorkflowHealthReport(AssuranceModel):
    """A concise AI workflow health DTO for delivery adapters."""

    healthy: bool
    state: str
    risk_level: Literal["low", "medium", "high"]
    ready: bool
    messages: tuple[str, ...] = ()


class WorkflowDiagnosticsReport(AssuranceModel):
    """Planning, dependency, execution, and architecture diagnostics for one Page."""

    health: WorkflowHealthReport
    planning: dict[str, Any] = Field(default_factory=dict)
    dependencies: dict[str, Any] = Field(default_factory=dict)
    execution: dict[str, Any] = Field(default_factory=dict)
    architecture: dict[str, Any] = Field(default_factory=dict)
    executive_summary: dict[str, Any] = Field(default_factory=dict)


class AIWorkflowDashboard(AssuranceModel):
    """Dashboard-ready workflow DTO with no presentation implementation."""

    state: str
    healthy: bool
    readiness: bool
    risk_level: Literal["low", "medium", "high"]


class ProviderDashboard(AssuranceModel):
    """Dashboard-ready Provider governance DTO."""

    default_provider: str
    healthy_providers: int = Field(ge=0)
    governance_valid: bool
    risk_level: Literal["low", "medium", "high"]


class EnterpriseDashboard(AssuranceModel):
    """Dashboard-ready enterprise readiness DTO."""

    ready: bool
    ready_areas: int = Field(ge=0)
    total_areas: int = Field(ge=0)


class OperationsDashboard(AssuranceModel):
    """Dashboard-ready operations evidence derived from Repository maintenance."""

    repository_healthy: bool
    projects: int = Field(ge=0)
    pages: int = Field(ge=0)


class ReleaseDashboard(AssuranceModel):
    """Release evidence DTO; it does not create a tag, build, or publish artifacts."""

    version: str
    release_ready: bool
    automatic_release: bool = False


class ExecutiveDashboardDTO(AssuranceModel):
    """Composite dashboard data for CLI, FastAPI, or MCP delivery only."""

    workflow: AIWorkflowDashboard
    provider: ProviderDashboard
    enterprise: EnterpriseDashboard
    operations: OperationsDashboard
    release: ReleaseDashboard


class WorkflowReliabilityAnalyzer:
    """Analyze reliability using planning data without controlling the workflow Engine."""

    def __init__(self, planning: PlanningService, workflow: WorkflowDependencyAnalyzer) -> None:
        self._planning = planning
        self._workflow = workflow

    def report(self, context: WorkflowContext) -> WorkflowReliabilityReport:
        analysis = self._workflow.analyze(context)
        history = context.metadata.get("workflow_history", [])
        history_entries = tuple(item for item in history if isinstance(item, Mapping)) if isinstance(history, list) else ()
        expected = analysis.score.completed_steps
        history_consistent = context.state.value == "Draft" or len(history_entries) >= expected
        missing_artifacts = tuple(
            artifact
            for step in analysis.dependency_graph.steps[:1]
            for artifact in step.requires_artifacts
            if artifact not in context.artifacts
        )
        integrity = WorkflowIntegrityAnalysis(
            valid=history_consistent and not missing_artifacts,
            current_state=context.state.value,
            history_consistent=history_consistent,
            required_artifacts_present=not missing_artifacts,
            findings=tuple(
                (["Persisted history is shorter than the completed StateMachine path."] if not history_consistent else [])
                + ([f"Required artifact is absent: {item}" for item in missing_artifacts])
            ),
        )
        recommendation = self._planning.workflow_intelligence(context).summary
        next_command = self._planning.summary(context).workflow.plan.recommendation.command
        validation = WorkflowValidationReport(
            valid=integrity.valid and analysis.bottlenecks.severity != "medium",
            next_command=next_command,
            approved_terminal=recommendation.terminal,
            messages=analysis.bottlenecks.bottlenecks,
        )
        consistency = WorkflowConsistencyAnalysis(
            consistent=history_consistent,
            observed_history_steps=len(history_entries),
            expected_completed_steps=expected,
            messages=integrity.findings,
        )
        risks = tuple((*analysis.bottlenecks.bottlenecks, *integrity.findings))
        level: Literal["low", "medium", "high"] = (
            "high" if not integrity.valid else "medium" if risks else "low"
        )
        risk = WorkflowRiskAssessment(
            level=level,
            risks=risks,
            mitigations=("Review diagnostics and execute only the StateMachine-recommended next step.",),
        )
        readiness = ExecutionReadinessReport(
            ready=validation.valid and not recommendation.terminal,
            next_command=next_command if validation.valid and not recommendation.terminal else None,
            reasons=("No workflow step was executed by this readiness report.", *risks),
        )
        return WorkflowReliabilityReport(
            integrity=integrity,
            validation=validation,
            consistency=consistency,
            risk=risk,
            readiness=readiness,
        )


class ProviderGovernance:
    """Read local Provider policy, metadata, lifecycle, and compatibility evidence."""

    def __init__(
        self, *, runtime: LLMProviderRuntime, optimizer: ProviderOptimizer, configuration: AppConfig
    ) -> None:
        self._runtime = runtime
        self._optimizer = optimizer
        self._configuration = configuration

    def report(self) -> ProviderGovernanceReport:
        optimization = self._optimizer.compare()
        metadata = tuple(self._runtime.discover())
        names = tuple(item.name for item in metadata)
        default = self._configuration.default_llm_provider
        policy = ProviderPolicyValidation(
            valid=default in names,
            default_provider=default,
            registered_providers=names,
            allowed_providers=names,
            messages=("Policy is diagnostic-only; registry registrations were not changed.",),
        )
        capability_index = {
            name: tuple(providers) for name, providers in self._runtime.capability_report().items()
        }
        capabilities = ProviderCapabilityAudit(
            capabilities=capability_index,
            providers_with_capabilities=sum(bool(item.capabilities) for item in metadata),
            valid=bool(metadata),
        )
        snapshots = self._runtime.health_snapshot()
        states = self._runtime.lifecycle().summary()
        healthy = sum(item.state.value == "healthy" for item in snapshots)
        lifecycle = ProviderLifecycleSummary(
            registered=len(snapshots), healthy=healthy, states=states
        )
        compatibility = ProviderCompatibilityReport(
            compatible=policy.valid and any(item.provider == default for item in optimization.comparisons),
            default_provider=default,
            recommendation=optimization.selection.selected_provider,
            messages=("Compatibility was determined from local protocol metadata and construction health.",),
        )
        risks = []
        if not policy.valid:
            risks.append("Configured default Provider is not registered.")
        if healthy == 0:
            risks.append("No Provider passed local construction health.")
        risk = ProviderRiskSummary(
            level="high" if len(risks) > 1 else "medium" if risks else "low",
            risks=tuple(risks),
            mitigations=("Review local configuration and registered Provider metadata before workflow execution.",),
        )
        return ProviderGovernanceReport(
            policy=policy,
            capabilities=capabilities,
            lifecycle=lifecycle,
            compatibility=compatibility,
            risk=risk,
            optimization=optimization,
        )


class EnterpriseReadiness:
    """Compose enterprise readiness areas without changing deployment or runtime state."""

    def __init__(
        self,
        *,
        configuration: AppConfig,
        workflow: WorkflowReliabilityAnalyzer,
        providers: ProviderGovernance,
        repository: RepositoryMaintenance,
    ) -> None:
        self._configuration = configuration
        self._workflow = workflow
        self._providers = providers
        self._repository = repository

    def report(self, context: WorkflowContext) -> EnterpriseReadinessReport:
        workflow = self._workflow.report(context)
        providers = self._providers.report()
        repository = self._repository.report()
        governance = configuration_governance(self._configuration)
        configuration = ReadinessArea(
            name="configuration",
            ready=governance.compatible and governance.integrity_valid,
            guidance="Validate the redacted configuration governance report before deployment.",
        )
        workflow_area = ReadinessArea(
            name="workflow",
            ready=workflow.validation.valid,
            guidance="Resolve workflow integrity or risk findings before executing one legal step.",
        )
        operations = ReadinessArea(
            name="operations",
            ready=providers.risk.level != "high" and repository.healthy,
            guidance="Review Provider governance and Repository maintenance evidence.",
        )
        maintenance = ReadinessArea(
            name="maintenance",
            ready=repository.healthy,
            guidance="Run Repository self-check before maintenance or resume work.",
        )
        recovery = ReadinessArea(
            name="recovery",
            ready=repository.healthy and workflow.consistency.consistent,
            guidance="Use existing recovery simulation before resuming exactly one Page step.",
        )
        deployment = ReadinessArea(
            name="deployment",
            ready=all(item.ready for item in (configuration, workflow_area, operations, maintenance, recovery)),
            guidance="This report is a checklist; it does not deploy or alter runtime state.",
        )
        return EnterpriseReadinessReport(
            ready=deployment.ready,
            deployment=deployment,
            operations=operations,
            maintenance=maintenance,
            configuration=configuration,
            recovery=recovery,
            workflow=workflow_area,
        )


class AssuranceService:
    """Application facade for reliability, governance, readiness, diagnostics, and dashboards."""

    def __init__(
        self,
        *,
        workflow: WorkflowReliabilityAnalyzer,
        providers: ProviderGovernance,
        enterprise: EnterpriseReadiness,
        planning: PlanningService,
        repository: RepositoryMaintenance,
    ) -> None:
        self._workflow = workflow
        self._providers = providers
        self._enterprise = enterprise
        self._planning = planning
        self._repository = repository

    def workflow_reliability(self, context: WorkflowContext) -> WorkflowReliabilityReport:
        return self._workflow.report(context)

    def provider_governance(self) -> ProviderGovernanceReport:
        return self._providers.report()

    def enterprise_readiness(self, context: WorkflowContext) -> EnterpriseReadinessReport:
        return self._enterprise.report(context)

    def workflow_diagnostics(self, context: WorkflowContext) -> WorkflowDiagnosticsReport:
        reliability = self.workflow_reliability(context)
        summary = self._planning.summary(context)
        health = WorkflowHealthReport(
            healthy=reliability.validation.valid,
            state=context.state.value,
            risk_level=reliability.risk.level,
            ready=reliability.readiness.ready,
            messages=(*reliability.risk.risks, *reliability.validation.messages),
        )
        return WorkflowDiagnosticsReport(
            health=health,
            planning=summary.workflow.model_dump(mode="json"),
            dependencies=summary.dependency_report.model_dump(mode="json"),
            execution=reliability.readiness.model_dump(mode="json"),
            architecture=summary.architecture_preview,
            executive_summary={"state": context.state.value, "healthy": health.healthy, "ready": health.ready},
        )

    def dashboard(self, context: WorkflowContext) -> ExecutiveDashboardDTO:
        reliability = self.workflow_reliability(context)
        providers = self.provider_governance()
        readiness = self.enterprise_readiness(context)
        repository = self._repository.report()
        ready_areas = sum(
            item.ready
            for item in (
                readiness.deployment,
                readiness.operations,
                readiness.maintenance,
                readiness.configuration,
                readiness.recovery,
                readiness.workflow,
            )
        )
        return ExecutiveDashboardDTO(
            workflow=AIWorkflowDashboard(
                state=context.state.value,
                healthy=reliability.validation.valid,
                readiness=reliability.readiness.ready,
                risk_level=reliability.risk.level,
            ),
            provider=ProviderDashboard(
                default_provider=providers.policy.default_provider,
                healthy_providers=providers.lifecycle.healthy,
                governance_valid=providers.policy.valid and providers.compatibility.compatible,
                risk_level=providers.risk.level,
            ),
            enterprise=EnterpriseDashboard(ready=readiness.ready, ready_areas=ready_areas, total_areas=6),
            operations=OperationsDashboard(
                repository_healthy=repository.healthy,
                projects=repository.statistics.projects,
                pages=repository.statistics.pages,
            ),
            release=ReleaseDashboard(version=__version__, release_ready=readiness.ready),
        )


def _title(name: str) -> str:
    parts: list[str] = []
    current = ""
    for character in name:
        if character.isupper() and current:
            parts.append(current)
            current = character
        else:
            current += character
    if current:
        parts.append(current)
    return " ".join(parts)


def _markdown(title: str, values: dict[str, Any]) -> str:
    lines = [f"# {title}", ""]
    for key, value in values.items():
        lines.extend([f"## {key.replace('_', ' ').title()}", "", "```json"])
        lines.append(json.dumps(value, indent=2, default=str))
        lines.extend(["```", ""])
    return "\n".join(lines)
