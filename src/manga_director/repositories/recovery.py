"""Repository-level validation and safe recovery helpers without adapter coupling."""

from __future__ import annotations

from manga_director.domain.exceptions import RepositoryError
from manga_director.repositories.integrity import IntegrityReport, ProjectIntegrityChecker
from manga_director.repositories.protocols import ProjectRepository


class RepositoryRecovery:
    """Inspect a persisted aggregate before an operator retries normal workflow work."""

    def __init__(
        self,
        repository: ProjectRepository,
        checker: ProjectIntegrityChecker | None = None,
    ) -> None:
        self._repository = repository
        self._checker = checker or ProjectIntegrityChecker()

    def inspect(self, project_id: str) -> IntegrityReport:
        return self._checker.check(self._repository.load(project_id))

    def validate_for_resume(self, project_id: str) -> IntegrityReport:
        report = self.inspect(project_id)
        if not report.valid:
            raise RepositoryError(
                f"Project '{project_id}' cannot resume until integrity errors are resolved: "
                + "; ".join(report.errors)
            )
        return report
