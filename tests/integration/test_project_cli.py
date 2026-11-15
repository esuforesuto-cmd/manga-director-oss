import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import manga_director.workflow.localfile_durable_routing as localfile_durable_routing
from manga_director.cli.app import app
from manga_director.domain.state_machine import PageState
from manga_director.repositories.local_file import LocalFileRepository


class _TestFence:
    def __init__(self, _project_id: str, _page_id: str) -> None:
        self.held = False

    def acquire(self) -> None:
        assert not self.held
        self.held = True

    def release(self) -> None:
        self.held = False


def _install_test_run_fence(monkeypatch: pytest.MonkeyPatch) -> None:
    route_localfile_run = localfile_durable_routing._route_localfile_run

    def route_with_test_fence(*args: object, **kwargs: object) -> object:
        kwargs["fence_factory"] = _TestFence
        return route_localfile_run(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(
        localfile_durable_routing, "_route_localfile_run", route_with_test_fence
    )


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_project_commands_and_export_import_round_trip(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    export_path = tmp_path / "export.yaml"
    common = ["--config", str(config)]

    create = runner.invoke(
        app,
        ["project", "create", "--id", "demo", "--title", "Demo Manga", *common],
    )
    open_result = runner.invoke(app, ["project", "open", "demo", *common])
    export = runner.invoke(
        app, ["project", "export", "demo", "--output", str(export_path), *common]
    )
    delete = runner.invoke(app, ["project", "delete", "demo", *common])
    import_result = runner.invoke(app, ["project", "import", "--source", str(export_path), *common])
    listed = runner.invoke(app, ["project", "list", *common])

    assert create.exit_code == 0
    assert '"title": "Demo Manga"' in create.stdout
    assert open_result.exit_code == 0
    assert export.exit_code == 0
    assert export_path.exists()
    assert delete.exit_code == 0
    assert import_result.exit_code == 0
    assert listed.exit_code == 0
    assert '"id": "demo"' in listed.stdout


def test_cli_project_workflow_persists_and_resumes_after_new_runtime(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]

    runner.invoke(app, ["project", "create", "--id", "demo", "--title", "Demo", *common])
    design = runner.invoke(app, ["design", "demo", "1", *common])
    resumed_status = runner.invoke(app, ["status", "demo", "1", *common])

    assert design.exit_code == 0
    assert '"current_state": "Designed"' in design.stdout
    assert resumed_status.exit_code == 0
    assert '"current_state": "Designed"' in resumed_status.stdout
    assert '"executable_step": "review"' in resumed_status.stdout


def test_cli_project_and_chapter_workflows_run_one_page_and_report_status(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]

    created = runner.invoke(app, ["project", "create", "--id", "demo", "--title", "Demo", *common])
    project_run = runner.invoke(app, ["project", "run", "demo", *common])
    project_status = runner.invoke(app, ["project", "status", "demo", *common])
    chapter_status = runner.invoke(app, ["chapter", "status", "demo", "chapter-1", *common])
    resumed = runner.invoke(app, ["project", "resume", "demo", *common])

    assert created.exit_code == 0
    assert project_run.exit_code == 0
    assert '"state": "QualityChecked"' in project_run.stdout
    assert project_status.exit_code == 0
    assert '"current_chapter": "chapter-1"' in project_status.stdout
    assert chapter_status.exit_code == 0
    assert '"current_page": 1' in chapter_status.stdout
    assert resumed.exit_code == 0
    assert '"state": "QualityChecked"' in resumed.stdout


def test_cli_project_execution_rejects_reserved_saved_metadata_before_page_transition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_test_run_fence(monkeypatch)
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]
    created = runner.invoke(app, ["project", "create", "--id", "demo", "--title", "Demo", *common])
    repository = LocalFileRepository(config.parent / ".manga-director")
    project = repository.load("demo")
    page = project.page(1).model_copy(
        update={"metadata": {"workflow_history": [{"_explicit_storyboard_input_authority": None}]}}
    )
    repository.save(project.replace_page(page))

    run = runner.invoke(app, ["project", "run", "demo", *common])
    status = runner.invoke(app, ["project", "status", "demo", *common])

    assert created.exit_code == 0
    assert run.exit_code == 1
    assert "DURABLE_EXECUTION_INPUT_INVALID" in run.stderr
    assert status.exit_code == 0
    assert repository.load("demo").page(1) == page
    assert repository.load("demo").page(1).state == PageState.DRAFT


def test_cli_localfile_batch_rejects_reserved_saved_metadata_and_retry_rechecks_it(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]
    created = runner.invoke(app, ["project", "create", "--id", "demo", "--title", "Demo", *common])
    repository = LocalFileRepository(config.parent / ".manga-director")
    project = repository.load("demo")
    page = project.page(1).model_copy(
        update={
            "metadata": {
                "workflow_history": [{"_explicit_storyboard_input_authority": "private-marker"}]
            }
        }
    )
    repository.save(project.replace_page(page))

    run = runner.invoke(app, ["batch", "run", "demo", "--id", "batch-1", *common])
    retry = runner.invoke(app, ["batch", "retry", "demo", "batch-1", *common])

    assert created.exit_code == 0
    assert run.exit_code == 0
    assert json.loads(run.stdout)["failed"] == [1]
    assert retry.exit_code == 0
    assert json.loads(retry.stdout)["failed"] == [1]
    assert "private-marker" not in run.stdout + retry.stdout
    assert repository.load("demo").page(1) == page


def test_cli_batch_commands_persist_and_report_a_sequential_batch(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]
    runner.invoke(app, ["project", "create", "--id", "demo", "--title", "Demo", *common])

    run = runner.invoke(app, ["batch", "run", "demo", "--id", "batch-1", *common])
    status = runner.invoke(app, ["batch", "status", "demo", "batch-1", *common])
    resume = runner.invoke(app, ["batch", "resume", "demo", "batch-1", *common])

    assert run.exit_code == 0
    assert '"status": "completed"' in run.stdout
    assert '"completed": [' in run.stdout
    assert status.exit_code == 0
    assert '"batch_id": "batch-1"' in status.stdout
    assert resume.exit_code == 0
    assert '"status": "completed"' in resume.stdout


def test_cli_project_status_reports_readiness_without_changing_localfile_bytes(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]
    created = runner.invoke(app, ["project", "create", "--id", "demo", "--title", "Demo", *common])
    projects = tmp_path / ".manga-director" / "projects"
    before = _tree_hashes(projects)

    status = runner.invoke(app, ["project", "status", "demo", *common])

    assert created.exit_code == 0
    assert status.exit_code == 0
    payload = json.loads(status.stdout)
    assert payload["current_chapter"] == "chapter-1"
    assert payload["current_page"] == 1
    assert payload["project"]["chapters"][0]["id"] == "chapter-1"
    assert payload["chapters"][0]["page_numbers"] == [1]
    assert payload["readiness_summary"] == {
        "completed_page_count": 0,
        "actionable_page_count": 1,
        "blocked_page_count": 0,
        "next_actionable_page_number": 1,
        "first_blocked_page": None,
        "next_actionable_page": payload["page_readiness"][0],
        "readiness_outcome": "ACTIONABLE",
        "readiness_focus_page": payload["page_readiness"][0],
    }
    assert payload["page_readiness"] == [
        {
            "page_number": 1,
            "current_state": "Draft",
            "unmet_prerequisites": [],
            "next_operation": "design",
            "non_execution": True,
        }
    ]
    assert _tree_hashes(projects) == before
