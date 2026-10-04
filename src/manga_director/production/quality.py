"""Read-only quality, repository-maintenance, and release-validation DTOs.

These application-layer helpers compose existing ports and contracts. They do
not execute Agents, transition pages, mutate repository data, or invoke network
providers.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from manga_director._version import __version__
from manga_director.cli.config import (
    AppConfig,
    ConfigurationGovernanceReport,
    configuration_governance,
)
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.repositories.integrity import RepositoryCheckReport, RepositorySelfCheck
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext

_MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]*\]\(([^)]+)\)")
_PUBLIC_API = frozenset(
    {
        "CLIError",
        "ConfigurationError",
        "Director",
        "ImageGenerator",
        "ImageGeneratorError",
        "ImageResult",
        "LLMProvider",
        "LLMResult",
        "MangaDirectorError",
        "Page",
        "Project",
        "PromptRequest",
        "PromptResponse",
        "Repository",
        "RepositoryError",
        "StateTransitionError",
        "ValidationError",
        "WorkflowContext",
        "WorkflowEngine",
        "WorkflowError",
        "__version__",
    }
)
_RELEASE_ASSETS = (
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "RELEASE_V3_1.md",
    "docs/SBOM.spdx.json",
    "docs/DEPENDENCY_LICENSE_REPORT.md",
    "docs/RELEASE_CHECKLIST_V3_1.md",
    "docs/COMPATIBILITY_V3_1.md",
)


class ValidationResult(BaseModel):
    """A transport-neutral validation result suitable for CI or diagnostics."""

    model_config = ConfigDict(frozen=True)

    name: str
    valid: bool
    checks: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    details: dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown(self.name.replace("_", " ").title(), self.model_dump(mode="json"))


class QualityDashboard(BaseModel):
    """Bounded summary of a set of validation DTOs."""

    model_config = ConfigDict(frozen=True)

    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    healthy: bool
    validation_names: tuple[str, ...] = ()


class QualityPipelineReport(BaseModel):
    """Composite quality automation report with JSON/Markdown renderers."""

    model_config = ConfigDict(frozen=True)

    results: tuple[ValidationResult, ...] = ()
    dashboard: QualityDashboard

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown("Quality Pipeline", self.model_dump(mode="json"))


class RepositoryStatistics(BaseModel):
    """Aggregate counts collected through the unchanged repository port."""

    model_config = ConfigDict(frozen=True)

    projects: int = Field(ge=0)
    chapters: int = Field(ge=0)
    pages: int = Field(ge=0)
    history_entries: int = Field(ge=0)
    state_counts: dict[str, int] = Field(default_factory=dict)


class RepositoryCleanupReport(BaseModel):
    """Read-only cleanup candidates; this report never deletes a Project."""

    model_config = ConfigDict(frozen=True)

    candidates: tuple[str, ...] = ()
    reasons: dict[str, str] = Field(default_factory=dict)
    destructive_action_performed: bool = False


class LargeRepositorySummary(BaseModel):
    """Largest persisted aggregate observations for operator planning."""

    model_config = ConfigDict(frozen=True)

    largest_project_id: str | None = None
    largest_project_pages: int = Field(default=0, ge=0)
    largest_history_entries: int = Field(default=0, ge=0)
    projects_scanned: int = Field(default=0, ge=0)


class RepositoryMaintenanceReport(BaseModel):
    """Repository statistics, integrity, cleanup candidates, and scale summary."""

    model_config = ConfigDict(frozen=True)

    statistics: RepositoryStatistics
    consistency: RepositoryCheckReport
    cleanup: RepositoryCleanupReport
    large_repository: LargeRepositorySummary

    @property
    def healthy(self) -> bool:
        return self.consistency.healthy

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown("Repository Maintenance", self.model_dump(mode="json"))


class DependencyInventory(BaseModel):
    """Declared package dependency inventory without inspecting host packages."""

    model_config = ConfigDict(frozen=True)

    runtime: tuple[str, ...] = ()
    optional: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    build: tuple[str, ...] = ()


class DevelopmentEnvironmentReport(BaseModel):
    """Safe development-environment details that exclude environment secrets."""

    model_config = ConfigDict(frozen=True)

    python_version: str
    workspace: str
    package_version: str
    source_present: bool
    tests_present: bool


class BuildSummary(BaseModel):
    """Static build metadata summary; it does not run a build command."""

    model_config = ConfigDict(frozen=True)

    build_backend: str
    version_source: str
    package_version: str
    source_distribution_includes_docs: bool


class DevelopmentDiagnosticsReport(BaseModel):
    """Development environment, dependency, build, and workspace evidence."""

    model_config = ConfigDict(frozen=True)

    environment: DevelopmentEnvironmentReport
    dependencies: DependencyInventory
    build: BuildSummary
    workspace: ValidationResult

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown("Development Diagnostics", self.model_dump(mode="json"))


class ProductionQualitySummary(BaseModel):
    """Presentation-independent release and maintenance status for operators."""

    model_config = ConfigDict(frozen=True)

    production_summary: dict[str, Any] = Field(default_factory=dict)
    quality_dashboard: QualityDashboard
    release_readiness: bool
    maintenance_summary: RepositoryMaintenanceReport

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown("Production Quality Summary", self.model_dump(mode="json"))


class RepositoryMaintenance:
    """Read-only repository operations built only on :class:`ProjectRepository`."""

    def __init__(self, repository: ProjectRepository, checker: RepositorySelfCheck | None = None) -> None:
        self._repository = repository
        self._checker = checker or RepositorySelfCheck(repository)

    def statistics(self) -> RepositoryStatistics:
        projects = self._repository.list()
        states = Counter(page.state.value for project in projects for page in project.pages)
        return RepositoryStatistics(
            projects=len(projects),
            chapters=sum(len(project.chapters) for project in projects),
            pages=sum(len(project.pages) for project in projects),
            history_entries=sum(len(page.history) for project in projects for page in project.pages),
            state_counts=dict(sorted(states.items())),
        )

    def cleanup_report(self) -> RepositoryCleanupReport:
        candidates: list[str] = []
        reasons: dict[str, str] = {}
        for project in self._repository.list():
            if not project.pages:
                candidates.append(project.id)
                reasons[project.id] = "project has no pages"
            elif project.metadata.get("maintenance_candidate") is True:
                candidates.append(project.id)
                reasons[project.id] = "project is explicitly marked for maintenance review"
        return RepositoryCleanupReport(candidates=tuple(candidates), reasons=reasons)

    def large_repository_summary(self) -> LargeRepositorySummary:
        projects = self._repository.list()
        if not projects:
            return LargeRepositorySummary(projects_scanned=0)
        largest = max(projects, key=lambda project: len(project.pages))
        return LargeRepositorySummary(
            largest_project_id=largest.id,
            largest_project_pages=len(largest.pages),
            largest_history_entries=max(
                (sum(len(page.history) for page in project.pages) for project in projects), default=0
            ),
            projects_scanned=len(projects),
        )

    def report(self, project_id: str | None = None) -> RepositoryMaintenanceReport:
        return RepositoryMaintenanceReport(
            statistics=self.statistics(),
            consistency=self._checker.check(project_id),
            cleanup=self.cleanup_report(),
            large_repository=self.large_repository_summary(),
        )


class QualityAutomation:
    """Compose read-only validation evidence for CI, developers, and operations."""

    def __init__(
        self,
        *,
        repository: ProjectRepository,
        configuration: AppConfig,
        root: Path,
        state_machine: StateMachine | None = None,
    ) -> None:
        self._repository = repository
        self._configuration = configuration
        self._root = root
        self._state_machine = state_machine or StateMachine()
        self._maintenance = RepositoryMaintenance(repository)

    def repository_validation(self, project_id: str | None = None) -> ValidationResult:
        report = self._maintenance.report(project_id)
        return ValidationResult(
            name="repository_validation",
            valid=report.healthy,
            checks=("repository_integrity", "repository_statistics", "large_repository_summary"),
            errors=tuple(report.consistency.errors),
            details=report.model_dump(mode="json"),
        )

    def workflow_validation(self, context: WorkflowContext) -> ValidationResult:
        errors: list[str] = []
        checks = ["single_page_context", "state_machine_read_only"]
        if "pages" in context.page:
            errors.append("WorkflowContext must represent one page, not a pages collection.")
        if context.state is not PageState.APPROVED:
            try:
                self._state_machine.next_command(context.state)
                checks.append("next_step_available")
            except Exception as exc:
                errors.append(str(exc))
        if context.state in {PageState.GENERATED, PageState.QUALITY_CHECKED, PageState.APPROVED}:
            if PageState.STORYBOARDED.value not in context.artifacts:
                errors.append("Generated-or-later workflow context requires a persisted storyboard artifact.")
            else:
                checks.append("storyboard_persisted")
        if context.state is PageState.APPROVED:
            if PageState.QUALITY_CHECKED.value not in context.artifacts:
                errors.append("Approved workflow context requires a completed quality artifact.")
            else:
                checks.append("quality_completed")
        return ValidationResult(
            name="workflow_validation",
            valid=not errors,
            checks=tuple(checks),
            errors=tuple(errors),
            details={"state": context.state.value, "mutated": False},
        )

    def configuration_validation(self) -> ValidationResult:
        governance: ConfigurationGovernanceReport = configuration_governance(self._configuration)
        valid = governance.compatible and governance.integrity_valid
        return ValidationResult(
            name="configuration_validation",
            valid=valid,
            checks=("schema_compatibility", "configuration_integrity", "secret_safe_fingerprint"),
            errors=tuple(governance.messages) if not valid else (),
            details=governance.model_dump(mode="json"),
        )

    def api_compatibility_validation(self) -> ValidationResult:
        import manga_director

        actual = frozenset(manga_director.__all__)
        missing = sorted(_PUBLIC_API - actual)
        unexpected = sorted(actual - _PUBLIC_API)
        errors = [*(f"missing public API: {name}" for name in missing)]
        errors.extend(f"unexpected public API: {name}" for name in unexpected)
        return ValidationResult(
            name="api_compatibility_validation",
            valid=not errors,
            checks=("root_public_api", "version_source"),
            errors=tuple(errors),
            details={"version": manga_director.__version__, "exports": sorted(actual)},
        )

    def documentation_validation(self) -> ValidationResult:
        documents = [self._root / "README.md", *(self._root / "docs").rglob("*.md")]
        missing_assets = [asset for asset in _RELEASE_ASSETS if not (self._root / asset).is_file()]
        missing_links = _missing_links(documents)
        errors = [*(f"missing release asset: {asset}" for asset in missing_assets)]
        errors.extend(missing_links)
        return ValidationResult(
            name="documentation_validation",
            valid=not errors,
            checks=("required_release_assets", "local_markdown_links"),
            errors=tuple(errors),
            details={"documents_checked": len(documents)},
        )

    def release_artifact_validation(self) -> ValidationResult:
        pyproject = tomllib.loads((self._root / "pyproject.toml").read_text(encoding="utf-8"))
        sbom = json.loads((self._root / "docs" / "SBOM.spdx.json").read_text(encoding="utf-8"))
        project = pyproject["project"]
        dynamic_version = project.get("dynamic") == ["version"]
        version_path = pyproject.get("tool", {}).get("hatch", {}).get("version", {}).get("path")
        sbom_version = str(sbom["packages"][0]["versionInfo"])
        errors: list[str] = []
        if not dynamic_version or version_path != "src/manga_director/_version.py":
            errors.append("Package version must be sourced from src/manga_director/_version.py.")
        if sbom_version != __version__:
            errors.append("SBOM package version does not match the package version.")
        return ValidationResult(
            name="release_artifact_validation",
            valid=not errors,
            checks=("dynamic_package_version", "sbom_version", "required_release_assets"),
            errors=tuple(errors),
            details={"package_version": __version__, "sbom_version": sbom_version},
        )

    def pipeline(self, context: WorkflowContext, project_id: str | None = None) -> QualityPipelineReport:
        results = (
            self.repository_validation(project_id),
            self.workflow_validation(context),
            self.configuration_validation(),
            self.api_compatibility_validation(),
            self.documentation_validation(),
            self.release_artifact_validation(),
        )
        dashboard = _dashboard(results)
        return QualityPipelineReport(results=results, dashboard=dashboard)

    def production_summary(
        self, context: WorkflowContext, project_id: str | None = None
    ) -> ProductionQualitySummary:
        pipeline = self.pipeline(context, project_id)
        maintenance = self._maintenance.report(project_id)
        return ProductionQualitySummary(
            production_summary={
                "mode": "local",
                "network_probes": False,
                "workflow_state": context.state.value,
                "repository_healthy": maintenance.healthy,
            },
            quality_dashboard=pipeline.dashboard,
            release_readiness=pipeline.dashboard.healthy and maintenance.healthy,
            maintenance_summary=maintenance,
        )


class DevelopmentDiagnostics:
    """Read-only workspace and declared-dependency diagnostics for contributors."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def dependency_inventory(self) -> DependencyInventory:
        pyproject = self._pyproject()
        project = pyproject["project"]
        optional = {
            str(name): tuple(str(value) for value in values)
            for name, values in project.get("optional-dependencies", {}).items()
        }
        build = tuple(str(value) for value in pyproject["build-system"]["requires"])
        return DependencyInventory(
            runtime=tuple(str(value) for value in project["dependencies"]),
            optional=optional,
            build=build,
        )

    def environment(self) -> DevelopmentEnvironmentReport:
        return DevelopmentEnvironmentReport(
            python_version=sys.version.split()[0],
            workspace=str(self._root),
            package_version=__version__,
            source_present=(self._root / "src" / "manga_director").is_dir(),
            tests_present=(self._root / "tests").is_dir(),
        )

    def build_summary(self) -> BuildSummary:
        pyproject = self._pyproject()
        sdist = pyproject.get("tool", {}).get("hatch", {}).get("build", {}).get("targets", {}).get("sdist", {})
        return BuildSummary(
            build_backend=str(pyproject["build-system"]["build-backend"]),
            version_source=str(pyproject["tool"]["hatch"]["version"]["path"]),
            package_version=__version__,
            source_distribution_includes_docs="/docs" in sdist.get("include", []),
        )

    def workspace_validation(self) -> ValidationResult:
        required = ("pyproject.toml", "README.md", "src/manga_director", "tests", "docs", "examples")
        missing = tuple(item for item in required if not (self._root / item).exists())
        return ValidationResult(
            name="workspace_validation",
            valid=not missing,
            checks=("workspace_layout", "typed_source", "documentation", "examples"),
            errors=tuple(f"missing workspace item: {item}" for item in missing),
            details={"root": str(self._root)},
        )

    def report(self) -> DevelopmentDiagnosticsReport:
        return DevelopmentDiagnosticsReport(
            environment=self.environment(),
            dependencies=self.dependency_inventory(),
            build=self.build_summary(),
            workspace=self.workspace_validation(),
        )

    def _pyproject(self) -> dict[str, Any]:
        return tomllib.loads((self._root / "pyproject.toml").read_text(encoding="utf-8"))


def _dashboard(results: Iterable[ValidationResult]) -> QualityDashboard:
    values = tuple(results)
    passed = sum(result.valid for result in values)
    return QualityDashboard(
        total=len(values),
        passed=passed,
        failed=len(values) - passed,
        healthy=passed == len(values),
        validation_names=tuple(result.name for result in values),
    )


def _missing_links(documents: Iterable[Path]) -> list[str]:
    missing: list[str] = []
    for document in documents:
        for raw_target in _MARKDOWN_LINK.findall(document.read_text(encoding="utf-8")):
            target = raw_target.split("#", 1)[0].strip().strip("<>")
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            if not (document.parent / target).resolve().exists():
                missing.append(f"broken local link: {document.name} -> {raw_target}")
    return missing


def _markdown(title: str, values: dict[str, Any]) -> str:
    lines = [f"# {title}", ""]
    for key, value in values.items():
        lines.extend([f"## {key.replace('_', ' ').title()}", "", "```json"])
        lines.append(json.dumps(value, indent=2, default=str))
        lines.extend(["```", ""])
    return "\n".join(lines)
