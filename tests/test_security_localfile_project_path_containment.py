from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from manga_director.domain.exceptions import ValidationError
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.mcp.contracts import CreateProjectInput, ProjectInput
from manga_director.mcp.registry import ToolDefinition, ToolRegistry
from manga_director.mcp.resources import McpResourceProvider
from manga_director.repositories import LocalFileRepository
from manga_director.repositories import _windows_safe_filesystem as windows_safe_module
from manga_director.repositories import local_file as local_file_module

_MALICIOUS_PROJECT_IDS = (
    "..",
    "../outside",
    "..\\outside",
    "/outside",
    "C:\\outside",
    "C:/outside",
    "C:relative",
    "\\\\server\\share\\outside.json",
    "\\\\?\\C:\\outside",
    "nested/mixed\\outside",
)


def _project(project_id: str = "demo-2026_09") -> Project:
    return Project(
        id=project_id,
        title="Security test",
        pages=[Page(page_number=1, state=PageState.DESIGNED, page_design={"purpose": "hook"})],
    )


@pytest.mark.parametrize("project_id", _MALICIOUS_PROJECT_IDS)
def test_direct_localfile_operations_reject_project_path_escapes(
    tmp_path: Path, project_id: str
) -> None:
    root = tmp_path / "trusted"
    repository = LocalFileRepository(root)
    repository.save(_project())
    outside = tmp_path / "outside.json"
    outside.write_text("outside sentinel", encoding="utf-8")

    for operation in (
        repository.load,
        repository.exists,
        repository.delete,
        lambda value: repository.load_page(value, 1),
    ):
        with pytest.raises(ValidationError):
            operation(project_id)

    with pytest.raises(ValidationError):
        repository.save(_project(project_id))

    assert outside.read_text(encoding="utf-8") == "outside sentinel"
    assert repository.load("demo-2026_09").id == "demo-2026_09"
    assert repository.exists("demo-2026_09") is True


def test_valid_project_operations_remain_inside_the_trusted_root(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path)
    project = _project()

    repository.save(project)

    assert repository.load(project.id) == project
    assert repository.exists(project.id) is True
    repository.delete(project.id)
    assert repository.exists(project.id) is False


def test_invalid_project_id_is_rejected_before_filesystem_indirection_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = LocalFileRepository(tmp_path)
    inspected_paths: list[Path] = []

    def record_inspection(path: Path) -> bool:
        inspected_paths.append(path)
        return False

    def reject_session_entry(self: object) -> None:
        raise AssertionError("filesystem session opened before project ID rejection")

    monkeypatch.setattr(local_file_module, "_is_reparse_point", record_inspection)
    monkeypatch.setattr(
        windows_safe_module._WindowsSafeSession,
        "__enter__",
        reject_session_entry,
    )

    with pytest.raises(ValidationError):
        repository.exists("../outside")

    assert inspected_paths == []


def test_localfile_rejects_existing_reparse_point_before_read_exists_or_delete(tmp_path: Path) -> None:
    repository = LocalFileRepository(tmp_path / "trusted")
    project = _project()
    repository.save(project)
    aggregate = repository._path(project.id)
    outside = tmp_path / "outside.json"
    outside.write_text("outside sentinel", encoding="utf-8")

    aggregate.unlink()
    try:
        aggregate.symlink_to(outside)
    except OSError:
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(local_file_module, "_is_reparse_point", lambda path: path == aggregate)
            original_open = (
                windows_safe_module._WindowsSafeSession._open_relative_validated
            )

            def reject_aggregate(self, parent, name, path, desired_access, *, directory):
                if path == aggregate:
                    raise ValidationError("Project path safety cannot be established.")
                return original_open(
                    self,
                    parent,
                    name,
                    path,
                    desired_access,
                    directory=directory,
                )

            monkeypatch.setattr(
                windows_safe_module._WindowsSafeSession,
                "_open_relative_validated",
                reject_aggregate,
            )
            _assert_reparse_rejected(repository, project.id)
    else:
        _assert_reparse_rejected(repository, project.id)

    assert outside.read_text(encoding="utf-8") == "outside sentinel"


def test_localfile_rejects_a_reparse_point_at_the_trusted_projects_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = LocalFileRepository(tmp_path / "trusted")
    repository._root.mkdir(parents=True)

    monkeypatch.setattr(
        local_file_module,
        "_is_reparse_point",
        lambda path: path == repository._root,
    )
    original_open = windows_safe_module._WindowsSafeSession._open_relative_validated

    def reject_root(self, parent, name, path, desired_access, *, directory):
        if name == "projects":
            raise ValidationError("Project path safety cannot be established.")
        return original_open(
            self,
            parent,
            name,
            path,
            desired_access,
            directory=directory,
        )

    monkeypatch.setattr(
        windows_safe_module._WindowsSafeSession,
        "_open_relative_validated",
        reject_root,
    )

    with pytest.raises(ValidationError):
        repository.exists("demo-2026_09")


def _assert_reparse_rejected(repository: LocalFileRepository, project_id: str) -> None:
    for operation in (repository.load, repository.exists, repository.delete):
        with pytest.raises(ValidationError):
            operation(project_id)


@pytest.mark.parametrize("project_id", _MALICIOUS_PROJECT_IDS)
@pytest.mark.parametrize("input_model", (ProjectInput, CreateProjectInput))
def test_mcp_tools_reject_invalid_project_ids_before_handlers_run(
    project_id: str, input_model: type[ProjectInput] | type[CreateProjectInput]
) -> None:
    calls: list[object] = []
    registry = ToolRegistry()
    registry.register(ToolDefinition("project", "security test", input_model, calls.append))
    arguments: dict[str, Any] = {"project_id": project_id}
    if input_model is CreateProjectInput:
        arguments["title"] = "Security test"

    result = registry.invoke("project", arguments)

    assert result.success is False
    assert result.errors[0].startswith("validation_error:")
    assert project_id not in result.errors[0]
    assert calls == []


def test_mcp_resource_rejects_invalid_project_id_before_service_access() -> None:
    service = _RecordingResourceService()
    resources = McpResourceProvider(service)  # type: ignore[arg-type]

    with pytest.raises(ValidationError, match="project_id is invalid"):
        resources.read("manga://projects/%2E%2E%5Coutside")

    assert service.get_project_calls == []


def test_mcp_contracts_do_not_depend_on_the_localfile_implementation() -> None:
    contracts_path = Path(__file__).parents[1] / "src/manga_director/mcp/contracts.py"
    tree = ast.parse(contracts_path.read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert "manga_director.repositories.local_file" not in imports


class _RecordingResourceService:
    def __init__(self) -> None:
        self.get_project_calls: list[str] = []

    def get_project(self, project_id: str) -> object:
        self.get_project_calls.append(project_id)
        raise AssertionError("invalid MCP resource must not reach the service")
