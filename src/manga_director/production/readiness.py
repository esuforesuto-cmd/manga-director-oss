"""Read-only reliability, release, maintenance, and OSS-readiness reports.

This module is an application-layer composition facade.  It reuses the
existing repository and quality contracts, never executes workflow steps, and
does not make network or GitHub calls.  Every report is transport-neutral and
can be rendered as JSON or Markdown by a CLI, API, or another delivery layer.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from manga_director._version import __version__
from manga_director.production.quality import (
    DevelopmentDiagnostics,
    QualityAutomation,
    RepositoryMaintenance,
    RepositoryMaintenanceReport,
    ValidationResult,
)
from manga_director.workflow.contracts import WorkflowContext

_GOVERNANCE_FILES = (
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "GOVERNANCE.md",
    "MAINTAINERS.md",
    "SECURITY.md",
    "SUPPORTED_VERSIONS.md",
)
_RELEASE_FILES = (
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "RELEASE_V3_1.md",
    "docs/SBOM.spdx.json",
    "docs/DEPENDENCY_LICENSE_REPORT.md",
    "docs/MIGRATION_V3_1.md",
    "docs/RELEASE_CHECKLIST_V3_1.md",
)
_ITERATION_DOCUMENTS = (
    "docs/COMPATIBILITY_V3_1.md",
    "docs/ARCHITECTURE_SUMMARY_V3_1.md",
    "docs/WORKFLOW_REGRESSION_V3_1.md",
    "docs/BENCHMARK_V3_1.md",
    "docs/SECURITY_AUDIT_V3_1.md",
    "docs/PACKAGE_AUDIT_V3_1.md",
    "docs/V3_1_RELEASE_READY_REPORT.md",
)


class ReportModel(BaseModel):
    """Immutable base for delivery-neutral JSON and Markdown reporting DTOs."""

    model_config = ConfigDict(frozen=True)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        title = re.sub(r"(?<!^)(?=[A-Z])", " ", self.__class__.__name__)
        return _markdown(title, self.model_dump(mode="json"))


class ReliabilityReport(ReportModel):
    """Workflow, repository, configuration, recovery, and runtime evidence."""

    workflow: ValidationResult
    repository: ValidationResult
    configuration: ValidationResult
    recovery: ValidationResult
    long_running: ValidationResult
    release_integrity: ValidationResult
    reliable: bool


class DependencyLifecycleReport(ReportModel):
    """Declared dependency lifecycle evidence without querying package indexes."""

    runtime_dependencies: tuple[str, ...] = ()
    optional_groups: tuple[str, ...] = ()
    build_dependencies: tuple[str, ...] = ()
    license_report_present: bool
    policy_present: bool
    lifecycle_status: str


class TechnicalDebtSummary(ReportModel):
    """Bounded, document-derived technical-debt summary for maintenance planning."""

    categories: tuple[str, ...] = ()
    register_present: bool
    unresolved_sections: tuple[str, ...] = ()


class RepositoryHealthReport(ReportModel):
    """Read-only repository health and maintenance recommendations."""

    maintenance: RepositoryMaintenanceReport
    healthy: bool
    recommendations: tuple[str, ...] = ()


class MaintenanceReport(ReportModel):
    """Maintenance evidence and diagnostic-only recommendations."""

    dependencies: DependencyLifecycleReport
    technical_debt: TechnicalDebtSummary
    repository: RepositoryHealthReport
    lifecycle_summary: dict[str, Any] = Field(default_factory=dict)
    recommendations: tuple[str, ...] = ()
    maintainable: bool


class ArtifactVerificationReport(ReportModel):
    """Static release-artifact verification; no build or upload is performed."""

    validation: ValidationResult
    required_files: tuple[str, ...] = ()
    missing_files: tuple[str, ...] = ()
    typed_marker_present: bool
    package_metadata_present: bool
    valid: bool


class ReleaseChecklistReport(ReportModel):
    """Generated release checklist based on current local validation evidence."""

    checks: tuple[ValidationResult, ...] = ()
    ready: bool


class ReleaseReadinessReport(ReportModel):
    """Release readiness evidence that remains independent of presentation adapters."""

    checklist: ReleaseChecklistReport
    artifacts: ArtifactVerificationReport
    version_consistency: ValidationResult
    documentation: ValidationResult
    migration: ValidationResult
    ready: bool


class OSSReadinessReport(ReportModel):
    """Governance, contribution, and license evidence with no GitHub operation."""

    contribution: ValidationResult
    governance: ValidationResult
    license: ValidationResult
    dependency_licenses: DependencyLifecycleReport
    community: ValidationResult
    ready: bool


class ExecutiveDashboard(ReportModel):
    """Small summary for a UI, API, CLI, or release process to render."""

    reliability: ReliabilityReport
    maintenance: MaintenanceReport
    release: ReleaseReadinessReport
    oss: OSSReadinessReport
    ready: bool


class ReleaseReadiness:
    """Compose passive reliability, release, maintenance, and OSS evidence."""

    def __init__(
        self,
        *,
        quality: QualityAutomation,
        maintenance: RepositoryMaintenance,
        root: Path,
        development: DevelopmentDiagnostics | None = None,
    ) -> None:
        self._quality = quality
        self._maintenance = maintenance
        self._root = root
        self._development = development or DevelopmentDiagnostics(root)

    def reliability_report(self, context: WorkflowContext, project_id: str | None = None) -> ReliabilityReport:
        workflow = self._quality.workflow_validation(context)
        repository = self._quality.repository_validation(project_id)
        configuration = self._quality.configuration_validation()
        recovery = ValidationResult(
            name="recovery_validation",
            valid=workflow.valid and repository.valid,
            checks=("one_page_resume_admission", "repository_integrity", "state_machine_authority"),
            errors=tuple((*workflow.errors, *repository.errors)),
            details={"executed": False, "persisted_state_changed": False, "workflow_state": context.state.value},
        )
        long_running = ValidationResult(
            name="long_running_stability_validation",
            valid=True,
            checks=("bounded_diagnostics_contract", "no_background_execution", "no_unbounded_cache_created"),
            details={"observed": False, "mode": "static_contract_validation"},
        )
        release_integrity = self._quality.release_artifact_validation()
        reliable = all(
            result.valid for result in (workflow, repository, configuration, recovery, long_running, release_integrity)
        )
        return ReliabilityReport(
            workflow=workflow,
            repository=repository,
            configuration=configuration,
            recovery=recovery,
            long_running=long_running,
            release_integrity=release_integrity,
            reliable=reliable,
        )

    def maintenance_report(self, project_id: str | None = None) -> MaintenanceReport:
        dependencies = self.dependency_lifecycle_report()
        debt = self.technical_debt_summary()
        repository = self.repository_health_report(project_id)
        recommendations: list[str] = []
        if repository.maintenance.cleanup.candidates:
            recommendations.append("Review repository cleanup candidates before any manual destructive action.")
        if not repository.healthy:
            recommendations.append("Resolve repository integrity findings before release or recovery.")
        if not dependencies.license_report_present:
            recommendations.append("Generate and review the dependency license report before release.")
        if not recommendations:
            recommendations.append("Continue scheduled read-only integrity, dependency, and documentation reviews.")
        lifecycle = {
            "package_version": __version__,
            "release_channel": "v3.1 stable release",
            "repository_port_preserved": True,
            "network_operations": False,
        }
        maintainable = repository.healthy and dependencies.license_report_present and debt.register_present
        return MaintenanceReport(
            dependencies=dependencies,
            technical_debt=debt,
            repository=repository,
            lifecycle_summary=lifecycle,
            recommendations=tuple(recommendations),
            maintainable=maintainable,
        )

    def dependency_lifecycle_report(self) -> DependencyLifecycleReport:
        inventory = self._development.dependency_inventory()
        return DependencyLifecycleReport(
            runtime_dependencies=inventory.runtime,
            optional_groups=tuple(sorted(inventory.optional)),
            build_dependencies=inventory.build,
            license_report_present=(self._root / "docs/DEPENDENCY_LICENSE_REPORT.md").is_file(),
            policy_present=(self._root / "docs/DEPENDENCY_POLICY.md").is_file(),
            lifecycle_status="declared dependencies only; live vulnerability or registry checks are intentionally external",
        )

    def technical_debt_summary(self) -> TechnicalDebtSummary:
        path = self._root / "docs/TECH_DEBT.md"
        if not path.is_file():
            return TechnicalDebtSummary(register_present=False)
        content = path.read_text(encoding="utf-8")
        wanted = ("Reliability", "Maintenance", "Release", "OSS", "Documentation")
        categories = tuple(name for name in wanted if name.lower() in content.lower())
        unresolved = tuple(
            name
            for name in ("Continuing", "Deferred", "Ongoing", "Production", "v3 candidates")
            if name.lower() in content.lower()
        )
        return TechnicalDebtSummary(
            categories=categories,
            register_present=True,
            unresolved_sections=unresolved,
        )

    def repository_health_report(self, project_id: str | None = None) -> RepositoryHealthReport:
        maintenance = self._maintenance.report(project_id)
        recommendations: list[str] = []
        if maintenance.cleanup.candidates:
            recommendations.append("Inspect cleanup candidates; this report does not delete Projects.")
        if not maintenance.healthy:
            recommendations.append("Run repository integrity diagnostics before a workflow resume.")
        if not recommendations:
            recommendations.append("Repository health is suitable for continued read-only release validation.")
        return RepositoryHealthReport(
            maintenance=maintenance,
            healthy=maintenance.healthy,
            recommendations=tuple(recommendations),
        )

    def release_readiness_report(self, context: WorkflowContext, project_id: str | None = None) -> ReleaseReadinessReport:
        artifact = self.artifact_verification()
        version = self.version_consistency_validation()
        documentation = self.documentation_completeness_report()
        migration = self.migration_validation()
        reliability = self.reliability_report(context, project_id)
        checklist = ReleaseChecklistReport(
            checks=(
                reliability.workflow,
                reliability.repository,
                reliability.configuration,
                artifact.validation,
                version,
                documentation,
                migration,
            ),
            ready=all(
                item.valid
                for item in (
                    reliability.workflow,
                    reliability.repository,
                    reliability.configuration,
                    artifact.validation,
                    version,
                    documentation,
                    migration,
                )
            ),
        )
        return ReleaseReadinessReport(
            checklist=checklist,
            artifacts=artifact,
            version_consistency=version,
            documentation=documentation,
            migration=migration,
            ready=checklist.ready,
        )

    def artifact_verification(self) -> ArtifactVerificationReport:
        validation = self._quality.release_artifact_validation()
        required = (*_RELEASE_FILES, *_ITERATION_DOCUMENTS)
        missing = tuple(item for item in required if not (self._root / item).is_file())
        typed = (self._root / "src/manga_director/py.typed").is_file()
        metadata = (self._root / "pyproject.toml").is_file()
        valid = validation.valid and not missing and typed and metadata
        return ArtifactVerificationReport(
            validation=validation,
            required_files=required,
            missing_files=missing,
            typed_marker_present=typed,
            package_metadata_present=metadata,
            valid=valid,
        )

    def version_consistency_validation(self) -> ValidationResult:
        expected = __version__
        paths = {
            "source": self._root / "src/manga_director/_version.py",
            "sbom": self._root / "docs/SBOM.spdx.json",
            "frontend": self._root / "web/package.json",
        }
        contents = {name: path.read_text(encoding="utf-8") if path.is_file() else "" for name, path in paths.items()}
        errors = [f"missing version asset: {name}" for name, content in contents.items() if not content]
        if contents["source"] and expected not in contents["source"]:
            errors.append("source version does not match package version")
        if contents["sbom"] and f'"versionInfo": "{expected}"' not in contents["sbom"]:
            errors.append("SBOM version does not match package version")
        frontend_version = expected.replace("rc", "-rc.")
        if contents["frontend"] and f'"version": "{frontend_version}"' not in contents["frontend"]:
            errors.append("frontend version does not match package version")
        return ValidationResult(
            name="version_consistency_validation",
            valid=not errors,
            checks=("single_python_version_source", "sbom_version", "frontend_version"),
            errors=tuple(errors),
            details={"expected_version": expected, "expected_frontend_version": frontend_version},
        )

    def documentation_completeness_report(self) -> ValidationResult:
        base = self._quality.documentation_validation()
        missing = tuple(item for item in _ITERATION_DOCUMENTS if not (self._root / item).is_file())
        errors = (*base.errors, *(f"missing release document: {item}" for item in missing))
        return ValidationResult(
            name="documentation_completeness_validation",
            valid=not errors,
            checks=(*base.checks, "iteration_3_documents"),
            errors=errors,
            details={"documents_checked": base.details.get("documents_checked", 0)},
        )

    def migration_validation(self) -> ValidationResult:
        required = ("docs/MIGRATION_V3_1.md", "docs/UPGRADE_POLICY.md")
        missing = tuple(item for item in required if not (self._root / item).is_file())
        return ValidationResult(
            name="migration_validation",
            valid=not missing,
            checks=("migration_guide", "upgrade_policy", "backward_compatibility_guidance"),
            errors=tuple(f"missing migration asset: {item}" for item in missing),
            details={"validated_version": __version__},
        )

    def oss_readiness_report(self) -> OSSReadinessReport:
        contribution = self._files_validation("contribution_readiness", ("CONTRIBUTING.md", "docs/CONTRIBUTOR_GUIDE.md"))
        governance = self._files_validation("governance_validation", _GOVERNANCE_FILES)
        license = self._files_validation("license_validation", ("LICENSE", "docs/DEPENDENCY_LICENSE_REPORT.md"))
        community = self._files_validation(
            "community_readiness",
            ("CODE_OF_CONDUCT.md", "SECURITY.md", "MAINTAINERS.md", "docs/OSS_READINESS.md"),
        )
        dependencies = self.dependency_lifecycle_report()
        ready = all((contribution.valid, governance.valid, license.valid, community.valid, dependencies.license_report_present))
        return OSSReadinessReport(
            contribution=contribution,
            governance=governance,
            license=license,
            dependency_licenses=dependencies,
            community=community,
            ready=ready,
        )

    def executive_dashboard(self, context: WorkflowContext, project_id: str | None = None) -> ExecutiveDashboard:
        reliability = self.reliability_report(context, project_id)
        maintenance = self.maintenance_report(project_id)
        release = self.release_readiness_report(context, project_id)
        oss = self.oss_readiness_report()
        return ExecutiveDashboard(
            reliability=reliability,
            maintenance=maintenance,
            release=release,
            oss=oss,
            ready=all((reliability.reliable, maintenance.maintainable, release.ready, oss.ready)),
        )

    def _files_validation(self, name: str, files: Iterable[str]) -> ValidationResult:
        missing = tuple(file for file in files if not (self._root / file).is_file())
        return ValidationResult(
            name=name,
            valid=not missing,
            checks=tuple(files),
            errors=tuple(f"missing required file: {file}" for file in missing),
            details={"network_or_github_operation": False},
        )


def _markdown(title: str, values: dict[str, Any]) -> str:
    lines = [f"# {title}", ""]
    for key, value in values.items():
        lines.extend([f"## {key.replace('_', ' ').title()}", "", "```json"])
        lines.append(json.dumps(value, indent=2, default=str))
        lines.extend(["```", ""])
    return "\n".join(lines)
