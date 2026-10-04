"""SQLAlchemy repository adapters; workflow code continues to use ProjectRepository."""

from __future__ import annotations

import json
from builtins import list as builtin_list
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    func,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

from manga_director.domain.exceptions import ProjectNotFoundError, RepositoryError
from manga_director.domain.project import Page, Project
from manga_director.observability.repository import RepositoryMetrics
from manga_director.repositories.protocols import ProjectRepository
from manga_director.repositories.queries import ProjectMetadata, page_history_slice
from manga_director.repositories.validator import ProjectValidator


class Base(DeclarativeBase):
    pass


class ProjectRecord(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    chapters: Mapped[list[ChapterRecord]] = relationship(cascade="all, delete-orphan")
    pages: Mapped[list[PageRecord]] = relationship(cascade="all, delete-orphan")


class ChapterRecord(Base):
    __tablename__ = "chapters"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class PageRecord(Base):
    __tablename__ = "pages"
    __table_args__ = (
        Index("ix_pages_project_page_number", "project_id", "page_number"),
        Index("ix_pages_project_state", "project_id", "state"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(64), nullable=False)
    artifacts: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str] = mapped_column("metadata", Text, nullable=False)
    history: Mapped[str] = mapped_column(Text, nullable=False)


class UnitOfWork:
    """Explicit transaction boundary for database repository operations."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self.session: Session | None = None

    def __enter__(self) -> UnitOfWork:
        self.session = self._session_factory()
        return self

    def commit(self) -> None:
        if self.session is not None:
            self.session.commit()

    def rollback(self) -> None:
        if self.session is not None:
            self.session.rollback()

    def close(self) -> None:
        if self.session is not None:
            self.session.close()
            self.session = None

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()


class DatabaseRepository(ProjectRepository):
    def __init__(
        self,
        url: str,
        *,
        engine: Engine | None = None,
        metrics: RepositoryMetrics | None = None,
    ) -> None:
        self._engine = engine or create_engine(
            url, future=True, pool_pre_ping=not url.startswith("sqlite")
        )
        self._sessions = sessionmaker(self._engine, expire_on_commit=False)
        self._validator = ProjectValidator()
        self.metrics = metrics or RepositoryMetrics(boundary="database")

    @property
    def engine(self) -> Engine:
        return self._engine

    def unit_of_work(self) -> UnitOfWork:
        return UnitOfWork(self._sessions)

    def create_schema(self) -> None:
        Base.metadata.create_all(self._engine)

    @contextmanager
    def transaction(self) -> Iterator[UnitOfWork]:
        with self.unit_of_work() as uow:
            yield uow

    def load(self, project_id: str) -> Project:
        return self.metrics.measure("load", lambda: self._load(project_id))

    def _load(self, project_id: str) -> Project:
        with self.unit_of_work() as uow:
            assert uow.session is not None
            record = uow.session.get(ProjectRecord, project_id)
            if record is None:
                raise ProjectNotFoundError(f"Project '{project_id}' does not exist.")
            return Project.model_validate(json.loads(record.payload))

    def save(self, project: Project) -> None:
        self.metrics.measure("save", lambda: self._save(project))

    def _save(self, project: Project) -> None:
        self._validator.validate(project)
        try:
            with self.unit_of_work() as uow:
                assert uow.session is not None
                record = uow.session.get(ProjectRecord, project.id)
                if record is None:
                    record = ProjectRecord(
                        id=project.id,
                        title=project.title,
                        payload="",
                        created_at=project.created_at,
                        updated_at=project.updated_at,
                    )
                    uow.session.add(record)
                payload = json.dumps(project.model_dump(mode="json"), ensure_ascii=False)
                if record.title != project.title:
                    record.title = project.title
                if record.payload != payload:
                    record.payload = payload
                if record.updated_at != project.updated_at:
                    record.updated_at = project.updated_at
                self._upsert_children(uow.session, project)
        except RepositoryError:
            raise
        except Exception as exc:
            raise RepositoryError(f"Unable to save project '{project.id}': {exc}") from exc

    def exists(self, project_id: str) -> bool:
        return self.metrics.measure("exists", lambda: self._exists(project_id))

    def _exists(self, project_id: str) -> bool:
        with self.unit_of_work() as uow:
            assert uow.session is not None
            return uow.session.get(ProjectRecord, project_id) is not None

    def delete(self, project_id: str) -> None:
        self.metrics.measure("delete", lambda: self._delete(project_id))

    def _delete(self, project_id: str) -> None:
        with self.unit_of_work() as uow:
            assert uow.session is not None
            record = uow.session.get(ProjectRecord, project_id)
            if record is None:
                raise ProjectNotFoundError(f"Project '{project_id}' does not exist.")
            uow.session.delete(record)

    def list(self) -> list[Project]:
        return self.metrics.measure("list", self._list)

    def _list(self) -> builtin_list[Project]:
        with self.unit_of_work() as uow:
            assert uow.session is not None
            return [
                Project.model_validate(json.loads(row.payload))
                for row in uow.session.scalars(select(ProjectRecord).order_by(ProjectRecord.id))
            ]

    def list_metadata(
        self, *, offset: int = 0, limit: int | None = None
    ) -> builtin_list[ProjectMetadata]:
        return self.metrics.measure("list_metadata", lambda: self._list_metadata(offset, limit))

    def _list_metadata(self, offset: int, limit: int | None) -> builtin_list[ProjectMetadata]:
        _validate_window(offset, limit)
        page_count = (
            select(func.count(PageRecord.id))
            .where(PageRecord.project_id == ProjectRecord.id)
            .correlate(ProjectRecord)
            .scalar_subquery()
        )
        chapter_count = (
            select(func.count(ChapterRecord.id))
            .where(ChapterRecord.project_id == ProjectRecord.id)
            .correlate(ProjectRecord)
            .scalar_subquery()
        )
        statement = (
            select(
                ProjectRecord.id,
                ProjectRecord.title,
                ProjectRecord.updated_at,
                page_count.label("page_count"),
                chapter_count.label("chapter_count"),
            )
            .order_by(ProjectRecord.id)
            .offset(offset)
        )
        if limit is not None:
            statement = statement.limit(limit)
        with self.unit_of_work() as uow:
            assert uow.session is not None
            return [
                ProjectMetadata(
                    id=row.id,
                    title=row.title,
                    page_count=row.page_count,
                    chapter_count=row.chapter_count,
                    updated_at=row.updated_at,
                )
                for row in uow.session.execute(statement).all()
            ]

    def load_page(self, project_id: str, page_number: int) -> Page:
        return self.metrics.measure("load_page", lambda: self._load_page(project_id, page_number))

    def _load_page(self, project_id: str, page_number: int) -> Page:
        with self.unit_of_work() as uow:
            assert uow.session is not None
            record = uow.session.scalar(
                select(PageRecord).where(
                    PageRecord.project_id == project_id, PageRecord.page_number == page_number
                )
            )
            if record is None:
                raise ProjectNotFoundError(
                    f"Page {page_number} does not exist in project '{project_id}'."
                )
            artifacts = json.loads(record.artifacts)
            return Page.model_validate(
                {
                    "page_number": record.page_number,
                    "state": record.state,
                    **artifacts,
                    "metadata": json.loads(record.metadata_json),
                    "history": json.loads(record.history),
                }
            )

    def load_history(
        self,
        project_id: str,
        page_number: int,
        *,
        offset: int = 0,
        limit: int | None = None,
    ) -> builtin_list[dict[str, object]]:
        return self.metrics.measure(
            "load_history",
            lambda: page_history_slice(
                self._load_page(project_id, page_number).history, offset=offset, limit=limit
            ),
        )

    @staticmethod
    def _upsert_children(session: Session, project: Project) -> None:
        chapters = {
            record.id: record
            for record in session.scalars(
                select(ChapterRecord).where(ChapterRecord.project_id == project.id)
            )
        }
        pages = {
            record.page_number: record
            for record in session.scalars(
                select(PageRecord).where(PageRecord.project_id == project.id)
            )
        }
        DatabaseRepository._sync_chapters(session, project, chapters)
        DatabaseRepository._sync_pages(session, project, pages)

    @staticmethod
    def _sync_chapters(
        session: Session, project: Project, existing: dict[str, ChapterRecord]
    ) -> None:
        current_chapter_ids = {f"{project.id}:{chapter.id}" for chapter in project.chapters}
        for record_id, chapter_record in existing.items():
            if record_id not in current_chapter_ids:
                session.delete(chapter_record)
        for chapter in project.chapters:
            record_id = f"{project.id}:{chapter.id}"
            payload = json.dumps(chapter.model_dump(mode="json"), ensure_ascii=False)
            existing_chapter = existing.get(record_id)
            if existing_chapter is None:
                session.add(
                    ChapterRecord(
                        id=record_id,
                        project_id=project.id,
                        title=chapter.title,
                        payload=payload,
                    )
                )
            else:
                if existing_chapter.title != chapter.title:
                    existing_chapter.title = chapter.title
                if existing_chapter.payload != payload:
                    existing_chapter.payload = payload

    @staticmethod
    def _sync_pages(session: Session, project: Project, existing: dict[int, PageRecord]) -> None:
        current_page_numbers = {page.page_number for page in project.pages}
        for page_number, page_record in existing.items():
            if page_number not in current_page_numbers:
                session.delete(page_record)
        for page in project.pages:
            artifacts = json.dumps(
                {
                    "page_design": page.page_design,
                    "review": page.review,
                    "storyboard": page.storyboard,
                    "dialogue": page.dialogue,
                    "prompt": page.prompt,
                    "image": page.image,
                    "quality": page.quality,
                    "continuity": page.continuity,
                    "approval": page.approval,
                    "events": [event.model_dump(mode="json") for event in page.events],
                },
                ensure_ascii=False,
            )
            metadata = json.dumps(page.metadata, ensure_ascii=False)
            history = json.dumps(page.history, ensure_ascii=False)
            existing_page = existing.get(page.page_number)
            if existing_page is None:
                session.add(
                    PageRecord(
                        project_id=project.id,
                        page_number=page.page_number,
                        state=page.state.value,
                        artifacts=artifacts,
                        metadata_json=metadata,
                        history=history,
                    )
                )
            else:
                if existing_page.state != page.state.value:
                    existing_page.state = page.state.value
                if existing_page.artifacts != artifacts:
                    existing_page.artifacts = artifacts
                if existing_page.metadata_json != metadata:
                    existing_page.metadata_json = metadata
                if existing_page.history != history:
                    existing_page.history = history


class SQLiteRepository(DatabaseRepository):
    def __init__(
        self, url: str = "sqlite:///:memory:", *, metrics: RepositoryMetrics | None = None
    ) -> None:
        if not url.startswith("sqlite"):
            raise ValueError("SQLiteRepository requires a sqlite URL.")
        super().__init__(url, metrics=metrics)


class PostgreSQLRepository(DatabaseRepository):
    def __init__(self, url: str, *, metrics: RepositoryMetrics | None = None) -> None:
        if not url.startswith(("postgresql", "postgres")):
            raise ValueError("PostgreSQLRepository requires a PostgreSQL URL.")
        super().__init__(url, metrics=metrics)


def _validate_window(offset: int, limit: int | None) -> None:
    if offset < 0 or (limit is not None and limit < 0):
        raise ValueError("offset and limit must be non-negative")
