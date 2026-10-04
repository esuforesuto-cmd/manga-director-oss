import hashlib
import json
from pathlib import Path

from typer.testing import CliRunner

from manga_director.cli.app import app


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
