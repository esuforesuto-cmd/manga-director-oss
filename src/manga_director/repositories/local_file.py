from __future__ import annotations

import json
import os
import re
import stat
from builtins import list as builtin_list
from pathlib import Path
from typing import Any

from manga_director.domain.exceptions import ProjectNotFoundError, ValidationError
from manga_director.domain.project import Page, Project
from manga_director.observability.repository import RepositoryMetrics
from manga_director.repositories._windows_safe_filesystem import WindowsSafeFilesystem
from manga_director.repositories.local_file_aggregate_envelope import (
    _decode_r27_aggregate,
    _project_payload_from_aggregate,
    _validate_revision_binding,
)
from manga_director.repositories.local_file_durability import (
    ConditionalCommitResult,
    LocalFileRevisionStore,
    RevisionedProjectSnapshot,
    _R27RevisionPublicationRequest,
)
from manga_director.repositories.protocols import ProjectRepository
from manga_director.repositories.queries import ProjectMetadata, page_history_slice
from manga_director.repositories.serializer import ProjectSerializer, SerializationFormat
from manga_director.repositories.validator import ProjectValidator


class LocalFileRepository(ProjectRepository):
    """Store validated Projects below a local root.

    Untrusted callers may supply project identifiers and may mutate the Windows
    filesystem namespace concurrently.  Windows reads, existence checks, and
    deletion therefore use pinned, reparse-safe handles for both validation and
    the actual operation.
    """

    def __init__(
        self,
        root: Path,
        *,
        format: SerializationFormat = "json",
        serializer: ProjectSerializer | None = None,
        validator: ProjectValidator | None = None,
        metrics: RepositoryMetrics | None = None,
    ) -> None:
        self._root = root / "projects"
        self._serializer = serializer or ProjectSerializer(format)
        self._validator = validator or ProjectValidator()
        self.metrics = metrics or RepositoryMetrics()
        self._revision_store = LocalFileRevisionStore(self._root)
        self._windows_safe_filesystem = (
            WindowsSafeFilesystem(self._root) if os.name == "nt" else None
        )
        # This opaque identity is only matched by the private R28 composition
        # handoff.  It is not inferred from a root, path, or DTO value.
        self._r27_repository_pair = object()

    @property
    def _suffix(self) -> str:
        return ".json" if self._serializer.format == "json" else ".yaml"

    def _path(self, project_id: str) -> Path:
        return self._contained_project_path(self._root / self._project_filename(project_id))

    def _project_filename(self, project_id: str) -> str:
        self._validate_project_id(project_id)
        return f"{project_id}{self._suffix}"

    @staticmethod
    def _validate_project_id(project_id: str) -> None:
        """Reject values that are not canonical project identifiers.

        This intentionally matches the existing persisted-project validation
        contract.  Project identifiers are data, never path components.
        """

        if (
            not isinstance(project_id, str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", project_id) is None
        ):
            raise ValidationError(
                "Project ID may contain only letters, numbers, hyphens, and underscores."
            )

    def _contained_project_path(self, candidate: Path) -> Path:
        """Reject pre-existing indirection below the trusted local root.

        The root is owner-controlled storage, not an authorization boundary
        against a principal that can rewrite filesystem entries concurrently.
        """

        absolute_root = self._root.absolute()
        absolute_candidate = candidate.absolute()
        try:
            relative = absolute_candidate.relative_to(absolute_root)
        except ValueError as exc:
            raise ValidationError("Project path must remain below the trusted projects root.") from exc
        self._reject_reparse_points(absolute_root, relative)
        try:
            resolved_root = absolute_root.resolve(strict=False)
            resolved_candidate = absolute_candidate.resolve(strict=False)
            resolved_candidate.relative_to(resolved_root)
        except (OSError, ValueError) as exc:
            raise ValidationError("Project path must remain below the trusted projects root.") from exc
        return candidate

    @staticmethod
    def _reject_reparse_points(root: Path, relative: Path) -> None:
        if _is_reparse_point(root):
            raise ValidationError("Project path contains an unsupported filesystem indirection.")
        current = root
        for component in relative.parts:
            current /= component
            if _is_reparse_point(current):
                raise ValidationError("Project path contains an unsupported filesystem indirection.")

    @property
    def _index_path(self) -> Path:
        return self._root / "_metadata_index.json"

    def _page_directory(self, project_id: str) -> Path:
        """Return the private page-document directory for selective reads."""

        self._validate_project_id(project_id)
        return self._contained_project_path(self._root / "_pages" / project_id)

    def _page_path(self, project_id: str, page_number: int) -> Path:
        return self._contained_project_path(
            self._page_directory(project_id) / f"{page_number}.json"
        )

    def _workflow_application_ledger_owner_root(self) -> Path:
        """Return the resolved private owner root for the Ledger sidecar.

        This is deliberately private LocalFile composition data.  It never
        accepts a caller path and remains distinct from revision metadata.
        """

        if not self._root.is_absolute():
            raise ValueError("trusted LocalFile durability root is unavailable")
        return self._root.resolve() / "_durability" / "_workflow_application_ledger"

    def _next_generation_normal_execution_owner_root(self) -> Path:
        """Return the trusted private root for Next Generation normal execution.

        This is private LocalFile composition data.  Individual Next Generation
        owners receive fixed child roots below this namespace; callers never
        supply a durability path.
        """

        if not self._root.is_absolute():
            raise ValueError("trusted LocalFile durability root is unavailable")
        return self._root.resolve() / "_durability" / "_next_generation_normal_execution"

    def load(self, project_id: str) -> Project:
        return self.metrics.measure("load", lambda: self._load(project_id))

    def _load(self, project_id: str) -> Project:
        filename = self._project_filename(project_id)
        try:
            if self._windows_safe_filesystem is not None:
                aggregate = self._windows_safe_filesystem.read_bytes(filename)
            else:
                aggregate = self._contained_project_path(self._root / filename).read_bytes()
            return self._deserialize_aggregate(aggregate)
        except FileNotFoundError as exc:
            raise ProjectNotFoundError(f"Project '{project_id}' does not exist.") from exc

    def _load_revisioned(self, project_id: str) -> RevisionedProjectSnapshot:
        """Load the authoritative aggregate with a private conditional-save token."""

        return self.metrics.measure(
            "load_revisioned",
            lambda: self._revision_store.load_snapshot(
                project_id,
                self._path(project_id),
                self._deserialize_aggregate,
                requires_existing_revision=self._r27_requires_existing_revision,
                validate_revision_record=lambda aggregate_bytes, record_project_id, record_revision, record_fingerprint: (
                    self._validate_r27_revision_binding(
                        aggregate_bytes,
                        record_project_id,
                        record_revision,
                        record_fingerprint,
                    )
                ),
            ),
        )

    def _conditional_commit(
        self, snapshot: RevisionedProjectSnapshot, project: Project
    ) -> ConditionalCommitResult:
        """Commit a complete aggregate only if its private revision is current.

        This is an internal durable-mode entry point.  The legacy ``save``
        method remains unchanged for existing V6 non-durable composition.
        """

        if snapshot.project.id != project.id:
            raise ValueError("revisioned snapshot project binding is invalid")
        self._validator.validate(project)
        serialized = self._serializer.dumps(project).encode("utf-8")
        revision = self.metrics.measure(
            "conditional_commit",
            lambda: self._revision_store.conditional_replace(
                snapshot,
                self._path(project.id),
                serialized,
                lambda payload: self._serializer.loads(payload.decode("utf-8")) == project,
            ),
        )
        return self._complete_conditional_commit(project, revision)

    def _conditional_commit_r27(
        self,
        snapshot: RevisionedProjectSnapshot,
        project: Project,
        request: _R27RevisionPublicationRequest,
    ) -> ConditionalCommitResult:
        """Private R28-only inlet for a sealed publication request."""

        if request.repository_pair is not self._r27_repository_pair:
            raise ValueError("r27 repository composition is invalid")
        if snapshot.project.id != project.id or request.project_id != project.id:
            raise ValueError("r27 revisioned project binding is invalid")
        self._validator.validate(project)
        serialized = self._serializer.dumps(project).encode("utf-8")
        revision = self.metrics.measure(
            "conditional_commit_r27",
            lambda: self._revision_store._conditional_replace_r27(
                snapshot,
                self._path(project.id),
                serialized,
                request,
                lambda aggregate: self._serializer.loads(
                    _project_payload_from_aggregate(aggregate).decode("utf-8")
                )
                == project,
            ),
        )
        return self._complete_conditional_commit(project, revision)

    def _activate_and_conditional_commit_r27(
        self,
        snapshot: RevisionedProjectSnapshot,
        project: Project,
        request: _R27RevisionPublicationRequest,
    ) -> ConditionalCommitResult:
        """Private R29-only first-publication inlet for canonical composition."""

        if request.repository_pair is not self._r27_repository_pair:
            raise ValueError("r27 repository composition is invalid")
        if snapshot.project.id != project.id or request.project_id != project.id:
            raise ValueError("r27 revisioned project binding is invalid")
        self._validator.validate(project)
        serialized = self._serializer.dumps(project).encode("utf-8")
        revision = self.metrics.measure(
            "activate_and_conditional_commit_r27",
            lambda: self._revision_store._activate_and_conditional_replace_r27(
                snapshot,
                self._path(project.id),
                serialized,
                request,
                lambda aggregate: self._serializer.loads(
                    _project_payload_from_aggregate(aggregate).decode("utf-8")
                )
                == project,
            ),
        )
        return self._complete_conditional_commit(project, revision)

    def _complete_conditional_commit(
        self, project: Project, revision: int
    ) -> ConditionalCommitResult:
        """Update non-authoritative derived material after an aggregate CAS."""

        warnings: list[str] = []
        try:
            self._save_page_documents(project)
        except Exception:
            warnings.append("derived_page_update_failed")
        try:
            index = self._read_index()
            metadata = self._metadata(project)
            if index.get(project.id) != metadata:
                index[project.id] = metadata
                self._write_index(index)
        except Exception:
            warnings.append("derived_metadata_index_update_failed")
        return ConditionalCommitResult(revision=revision, derived_warnings=tuple(warnings))

    def _load_authoritative_page(self, project_id: str, page_number: int) -> Page:
        """Return a page from the aggregate; never trust derived page documents."""

        return self._load(project_id).page(page_number)

    def save(self, project: Project) -> None:
        self.metrics.measure("save", lambda: self._save(project))

    def _save(self, project: Project) -> None:
        self._validator.validate(project)
        path = self._path(project.id)
        serialized = self._serializer.dumps(project).encode("utf-8")
        self._revision_store._replace_raw_legacy(project.id, path, serialized)
        index = self._read_index()
        metadata = self._metadata(project)
        if index.get(project.id) != metadata:
            index[project.id] = metadata
            self._write_index(index)
        self._save_page_documents(project)

    def exists(self, project_id: str) -> bool:
        return self.metrics.measure("exists", lambda: self._exists(project_id))

    def _exists(self, project_id: str) -> bool:
        filename = self._project_filename(project_id)
        if self._windows_safe_filesystem is not None:
            return self._windows_safe_filesystem.exists(filename)
        return self._contained_project_path(self._root / filename).exists()

    def delete(self, project_id: str) -> None:
        self.metrics.measure("delete", lambda: self._delete(project_id))

    def _delete(self, project_id: str) -> None:
        filename = self._project_filename(project_id)
        if self._windows_safe_filesystem is not None:
            try:
                self._windows_safe_filesystem.delete_project(filename, project_id)
            except FileNotFoundError as exc:
                raise ProjectNotFoundError(f"Project '{project_id}' does not exist.") from exc
            return
        path = self._path(project_id)
        try:
            path.unlink()
        except FileNotFoundError as exc:
            raise ProjectNotFoundError(f"Project '{project_id}' does not exist.") from exc
        index = self._read_index()
        if project_id in index:
            del index[project_id]
            self._write_index(index)
        page_directory = self._page_directory(project_id)
        if page_directory.exists():
            for page_path in page_directory.glob("*.json"):
                page_path.unlink()
            page_directory.rmdir()

    def list(self) -> list[Project]:
        return self.metrics.measure(
            "list",
            lambda: [
                self._deserialize_aggregate(path.read_bytes())
                for path in self._project_paths()
            ],
        )

    def list_metadata(
        self, *, offset: int = 0, limit: int | None = None
    ) -> builtin_list[ProjectMetadata]:
        return self.metrics.measure("list_metadata", lambda: self._list_metadata(offset, limit))

    def _list_metadata(self, offset: int, limit: int | None) -> builtin_list[ProjectMetadata]:
        _validate_window(offset, limit)
        index = self._read_index()
        records = [index[key] for key in sorted(index)]
        return records[offset : None if limit is None else offset + limit]

    def load_page(self, project_id: str, page_number: int) -> Page:
        return self.metrics.measure("load_page", lambda: self._load_page(project_id, page_number))

    def _load_page(self, project_id: str, page_number: int) -> Page:
        try:
            return Page.model_validate_json(
                self._page_path(project_id, page_number).read_text(encoding="utf-8")
            )
        except FileNotFoundError:
            # Projects written before selective page documents remain readable.
            return self._load(project_id).page(page_number)

    def load_history(
        self,
        project_id: str,
        page_number: int,
        *,
        offset: int = 0,
        limit: int | None = None,
    ) -> builtin_list[dict[str, Any]]:
        return self.metrics.measure(
            "load_history",
            lambda: page_history_slice(
                self._load_page(project_id, page_number).history, offset=offset, limit=limit
            ),
        )

    def _save_page_documents(self, project: Project) -> None:
        """Persist only changed page documents so page reads do not deserialize an aggregate."""

        page_directory = self._page_directory(project.id)
        page_directory.mkdir(parents=True, exist_ok=True)
        page_numbers = {page.page_number for page in project.pages}
        for page_path in page_directory.glob("*.json"):
            if page_path.stem.isdigit() and int(page_path.stem) not in page_numbers:
                page_path.unlink()
        for page in project.pages:
            path = self._page_path(project.id, page.page_number)
            serialized = page.model_dump_json()
            try:
                if path.read_text(encoding="utf-8") == serialized:
                    continue
            except FileNotFoundError:
                pass
            temporary = path.with_suffix(".json.tmp")
            temporary.write_text(serialized, encoding="utf-8")
            temporary.replace(path)

    def _project_paths(self) -> builtin_list[Path]:
        return [
            path
            for path in sorted(self._root.glob(f"*{self._suffix}"))
            if path.name != self._index_path.name
        ]

    def _read_index(self) -> dict[str, ProjectMetadata]:
        try:
            raw = json.loads(self._index_path.read_text(encoding="utf-8"))
            return {key: ProjectMetadata.model_validate(value) for key, value in raw.items()}
        except FileNotFoundError:
            index = {
                project.id: self._metadata(project)
                for project in (
                    self._deserialize_aggregate(path.read_bytes())
                    for path in self._project_paths()
                )
            }
            if index:
                self._write_index(index)
            return index

    def _write_index(self, index: dict[str, ProjectMetadata]) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps({key: value.model_dump(mode="json") for key, value in index.items()})
        try:
            if self._index_path.read_text(encoding="utf-8") == serialized:
                return
        except FileNotFoundError:
            pass
        temporary = self._index_path.with_suffix(".json.tmp")
        temporary.write_text(serialized, encoding="utf-8")
        temporary.replace(self._index_path)

    @staticmethod
    def _metadata(project: Project) -> ProjectMetadata:
        return ProjectMetadata(
            id=project.id,
            title=project.title,
            page_count=len(project.pages),
            chapter_count=len(project.chapters),
            updated_at=project.updated_at,
        )

    def _deserialize_aggregate(self, aggregate_bytes: bytes) -> Project:
        payload = _project_payload_from_aggregate(aggregate_bytes)
        return self._serializer.loads(payload.decode("utf-8"))

    @staticmethod
    def _r27_requires_existing_revision(aggregate_bytes: bytes) -> bool:
        return _decode_r27_aggregate(aggregate_bytes) is not None

    def _validate_r27_revision_binding(
        self,
        aggregate_bytes: bytes,
        record_project_id: str,
        record_revision: int,
        record_fingerprint: str,
    ) -> None:
        _validate_revision_binding(
            aggregate_bytes,
            record_project_id=record_project_id,
            record_revision=record_revision,
            record_fingerprint=record_fingerprint,
            project_id_reader=lambda payload: self._serializer.loads(payload.decode("utf-8")).id,
        )


def _validate_window(offset: int, limit: int | None) -> None:
    if offset < 0 or (limit is not None and limit < 0):
        raise ValueError("offset and limit must be non-negative")


def _is_reparse_point(path: Path) -> bool:
    """Return whether an existing path component is a link/reparse point.

    ``lstat`` avoids following an attacker-controlled filesystem indirection.
    The Windows reparse attribute covers junctions in addition to symbolic
    links; on other supported platforms the symbolic-link mode remains enough.
    """

    try:
        path_status = path.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise ValidationError("Project path safety cannot be established.") from exc
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(path_status.st_mode) or bool(
        getattr(path_status, "st_file_attributes", 0) & reparse_attribute
    )
