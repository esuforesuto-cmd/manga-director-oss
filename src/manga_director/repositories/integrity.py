"""Read-only aggregate integrity checks shared by repository recovery paths."""

from __future__ import annotations

from pydantic import BaseModel, Field

from manga_director.domain.project import Project
from manga_director.repositories.protocols import ProjectRepository
from manga_director.repositories.validator import ProjectValidator


class IntegrityReport(BaseModel):
    """Safe result of validating a persisted Project aggregate."""

    project_id: str
    valid: bool
    checks: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class RepositoryCheckReport(BaseModel):
    """Bounded, safe repository self-check result for operations tooling."""

    healthy: bool
    projects_checked: int = Field(ge=0)
    valid_projects: int = Field(ge=0)
    reports: list[IntegrityReport] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ProjectIntegrityChecker:
    """Validate Project, metadata, history, and persisted workflow snapshots."""

    def __init__(self, validator: ProjectValidator | None = None) -> None:
        self._validator = validator or ProjectValidator()

    def check(self, project: Project) -> IntegrityReport:
        checks: list[str] = []
        errors: list[str] = []
        try:
            self._validator.validate(project)
            checks.append("project_invariants")
        except Exception as exc:
            errors.append(str(exc))
        for page in project.pages:
            self._check_page(page.page_number, page.metadata, page.history, errors, checks)
        self._check_metadata(project.metadata, errors, checks)
        self._check_snapshot(project.workflow, errors, checks)
        return IntegrityReport(
            project_id=project.id,
            valid=not errors,
            checks=checks,
            errors=errors,
        )

    @staticmethod
    def _check_page(
        page_number: int,
        metadata: dict[str, object],
        history: list[dict[str, object]],
        errors: list[str],
        checks: list[str],
    ) -> None:
        if not isinstance(metadata, dict):
            errors.append(f"Page {page_number} metadata must be a mapping.")
        if not all(isinstance(entry, dict) for entry in history):
            errors.append(f"Page {page_number} history must contain mappings.")
        else:
            checks.append(f"page_{page_number}_history")

    @staticmethod
    def _check_snapshot(
        workflow: dict[str, object], errors: list[str], checks: list[str]
    ) -> None:
        batches = workflow.get("batches")
        if batches is not None and not isinstance(batches, dict):
            errors.append("Workflow batches snapshot must be a mapping.")
        else:
            checks.append("workflow_snapshot")

    @staticmethod
    def _check_metadata(metadata: dict[str, object], errors: list[str], checks: list[str]) -> None:
        if not isinstance(metadata, dict):
            errors.append("Project metadata must be a mapping.")
            return
        if any(not isinstance(key, str) or not key.strip() for key in metadata):
            errors.append("Project metadata keys must be non-empty strings.")
            return
        checks.append("project_metadata")


class RepositorySelfCheck:
    """Validate persisted aggregates through the unchanged repository protocol."""

    def __init__(
        self,
        repository: ProjectRepository,
        checker: ProjectIntegrityChecker | None = None,
    ) -> None:
        self._repository = repository
        self._checker = checker or ProjectIntegrityChecker()

    def check(self, project_id: str | None = None, *, limit: int = 100) -> RepositoryCheckReport:
        if limit <= 0:
            raise ValueError("limit must be positive")
        try:
            projects = (
                [self._repository.load(project_id)]
                if project_id is not None
                else self._repository.list()[:limit]
            )
        except Exception as exc:
            return RepositoryCheckReport(
                healthy=False,
                projects_checked=0,
                valid_projects=0,
                errors=[str(exc)],
            )
        reports = [self._checker.check(project) for project in projects]
        valid = sum(report.valid for report in reports)
        return RepositoryCheckReport(
            healthy=valid == len(reports),
            projects_checked=len(reports),
            valid_projects=valid,
            reports=reports,
            errors=[error for report in reports for error in report.errors],
        )
