"""Repository port and built-in persistence adapters."""

from manga_director.repositories.database import (
    DatabaseRepository,
    PostgreSQLRepository,
    SQLiteRepository,
    UnitOfWork,
)
from manga_director.repositories.database_factory import DatabaseFactory
from manga_director.repositories.integrity import (
    IntegrityReport,
    ProjectIntegrityChecker,
    RepositoryCheckReport,
    RepositorySelfCheck,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.memory import InMemoryRepository
from manga_director.repositories.project_loader import ProjectLoader
from manga_director.repositories.protocols import ProjectRepository
from manga_director.repositories.queries import ProjectMetadata, ProjectQueryRepository
from manga_director.repositories.recovery import RepositoryRecovery
from manga_director.repositories.scalability import (
    HistoryPage,
    ProjectScanSummary,
    RepositoryIndex,
    RepositoryScalability,
)

__all__ = [
    "DatabaseFactory",
    "DatabaseRepository",
    "InMemoryRepository",
    "IntegrityReport",
    "LocalFileRepository",
    "PostgreSQLRepository",
    "ProjectLoader",
    "ProjectIntegrityChecker",
    "ProjectMetadata",
    "ProjectQueryRepository",
    "ProjectRepository",
    "RepositoryRecovery",
    "RepositoryCheckReport",
    "RepositorySelfCheck",
    "RepositoryIndex",
    "RepositoryScalability",
    "ProjectScanSummary",
    "HistoryPage",
    "SQLiteRepository",
    "UnitOfWork",
]
