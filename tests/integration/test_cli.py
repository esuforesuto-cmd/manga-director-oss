from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from typer.testing import CliRunner

from manga_director.cli.app import app
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow.contracts import WorkflowResult
from manga_director.workflow.durable_execution import (
    DurableWorkflowExecutionCoordinator,
    LocalFileDurablePageStore,
    LogicalOutputAssetQualityGatePort,
)
from manga_director.workflow.engine import WorkflowEngine


class _Fence:
    def __init__(self, _project_id: str, _page_id: str) -> None:
        self.held = False

    def acquire(self) -> None:
        assert self.held is False
        self.held = True

    def release(self) -> None:
        self.held = False


def _route_with_test_fence(
    engine: WorkflowEngine,
    repository: LocalFileRepository,
    project_id: str,
    page_id: str,
    command: str,
    execution_input: dict[str, Any],
    *,
    logical_output_asset_quality_gate: LogicalOutputAssetQualityGatePort | None = None,
) -> WorkflowResult:
    receipt = DurableWorkflowExecutionCoordinator(
        engine,
        LocalFileDurablePageStore(repository),
        fence_factory=_Fence,
        logical_output_asset_quality_gate=logical_output_asset_quality_gate,
    )._execute_with_receipt(project_id, page_id, command, execution_input)
    assert receipt.workflow_result is not None
    return receipt.workflow_result


def _advance_to_prompt_built(runner: CliRunner, config: Path) -> None:
    common = ["--config", str(config)]
    assert runner.invoke(app, ["init", "--project", "demo", "--page", "001", *common]).exit_code == 0
    repository = LocalFileRepository(config.parent / ".manga-director")
    repository.save(
        Project(
            id="demo",
            title="demo",
            pages=[
                Page(
                    page_number=1,
                    state=PageState.PROMPT_BUILT,
                    page_design={},
                    review={},
                    storyboard={"panels": [{"panel": 1}]},
                    prompt={"prompt_markdown": "one monochrome manga panel"},
                )
            ],
        )
    )


def test_cli_generate_default_keeps_existing_mock_route(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    _advance_to_prompt_built(runner, config)

    def unexpected_real_generation(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("default generate must not enter the real-provider path")

    monkeypatch.setattr(
        "manga_director.cli.app.execute_localfile_real_image_generation",
        unexpected_real_generation,
    )
    monkeypatch.setattr(
        "manga_director.cli.app._route_localfile_primary", _route_with_test_fence
    )
    result = runner.invoke(
        app, ["generate", "demo", "001", "--config", str(config)]
    )

    assert result.exit_code == 0
    assert '"current_state": "Generated"' in result.stdout
    assert '"provider": "mock"' in result.stdout


def test_cli_generate_explicit_openai_opt_in_requires_and_forwards_human_authorization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    _advance_to_prompt_built(runner, config)
    calls: list[tuple[str, str, str]] = []

    class _Report(SimpleNamespace):
        def model_dump(self, *, mode: str) -> dict[str, object]:
            assert mode == "json"
            return {
                "status": self.status,
                "completed": self.completed,
                "provider_invocation_performed": True,
                "external_application_delegated": self.external_application_delegated,
            }

    def execute_real(
        _repository: object,
        _engine: object,
        project: str,
        page: str,
        authorized_by: str,
    ) -> object:
        calls.append((project, page, authorized_by))
        return _Report(
            status="completed",
            completed=True,
            external_application_delegated=True,
            findings=(),
        )

    monkeypatch.setattr(
        "manga_director.cli.app.execute_localfile_real_image_generation", execute_real
    )
    result = runner.invoke(
        app,
        [
            "generate",
            "demo",
            "001",
            "--real-provider",
            "openai",
            "--authorized-by",
            "human:editor",
            "--config",
            str(config),
        ],
    )

    assert result.exit_code == 0
    assert calls == [("demo", "001", "human:editor")]
    assert '"completed": true' in result.stdout


def test_cli_generate_explicit_comfyui_opt_in_is_separate_and_forwards_authorization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    _advance_to_prompt_built(runner, config)
    calls: list[tuple[str, str, str]] = []

    class _Report(SimpleNamespace):
        def model_dump(self, *, mode: str) -> dict[str, object]:
            assert mode == "json"
            return {
                "status": self.status,
                "completed": self.completed,
                "provider_invocation_performed": True,
                "external_application_delegated": self.external_application_delegated,
            }

    def execute_comfyui(
        _repository: object,
        _engine: object,
        project: str,
        page: str,
        authorized_by: str,
    ) -> object:
        calls.append((project, page, authorized_by))
        return _Report(
            status="completed",
            completed=True,
            external_application_delegated=True,
            findings=(),
        )

    def unexpected_openai(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("ComfyUI selection must not switch to OpenAI")

    monkeypatch.setattr(
        "manga_director.cli.app.execute_localfile_comfyui_real_image_generation",
        execute_comfyui,
    )
    monkeypatch.setattr(
        "manga_director.cli.app.execute_localfile_real_image_generation",
        unexpected_openai,
    )
    result = runner.invoke(
        app,
        [
            "generate",
            "demo",
            "001",
            "--real-provider",
            "comfyui",
            "--authorized-by",
            "human:editor",
            "--config",
            str(config),
        ],
    )

    assert result.exit_code == 0
    assert calls == [("demo", "001", "human:editor")]
    assert '"completed": true' in result.stdout


def test_cli_generate_explicit_comfyui_resolves_relative_repository_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    config = Path("config.yaml")
    _advance_to_prompt_built(runner, config)
    observed_roots: list[Path] = []

    class _Report(SimpleNamespace):
        def model_dump(self, *, mode: str) -> dict[str, object]:
            assert mode == "json"
            return {
                "status": self.status,
                "completed": self.completed,
                "provider_invocation_performed": True,
                "external_application_delegated": self.external_application_delegated,
            }

    def execute_comfyui(
        repository: object,
        _engine: object,
        project: str,
        page: str,
        authorized_by: str,
    ) -> object:
        assert isinstance(repository, LocalFileRepository)
        observed_roots.append(repository._root)
        assert (project, page, authorized_by) == ("demo", "001", "human:editor")
        return _Report(
            status="completed",
            completed=True,
            external_application_delegated=True,
            findings=(),
        )

    monkeypatch.setattr(
        "manga_director.cli.app.execute_localfile_comfyui_real_image_generation",
        execute_comfyui,
    )
    result = runner.invoke(
        app,
        [
            "generate",
            "demo",
            "001",
            "--real-provider",
            "comfyui",
            "--authorized-by",
            "human:editor",
            "--config",
            "config.yaml",
        ],
    )

    assert result.exit_code == 0
    assert observed_roots == [(tmp_path / ".manga-director" / "projects").resolve()]
    assert observed_roots[0].is_absolute()


@pytest.mark.parametrize(
    "extra",
    (
        ["--real-provider", "other", "--authorized-by", "human:editor"],
        ["--real-provider", "openai"],
        ["--authorized-by", "human:editor"],
    ),
)
def test_cli_generate_invalid_real_opt_in_never_enters_provider_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extra: list[str],
) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    calls = 0

    def unexpected(*_args: object, **_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        raise AssertionError

    monkeypatch.setattr(
        "manga_director.cli.app.execute_localfile_real_image_generation", unexpected
    )
    result = runner.invoke(
        app, ["generate", "missing", "1", *extra, "--config", str(config)]
    )

    assert result.exit_code == 1
    assert calls == 0


def test_cli_run_status_and_explicit_approval(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]

    init_result = runner.invoke(app, ["init", "--project", "demo", "--page", "001", *common])
    run_result = runner.invoke(app, ["run", "demo", "001", *common])
    status_result = runner.invoke(app, ["status", "demo", "001", *common])
    approval_result = runner.invoke(
        app,
        ["approve", "demo", "001", "--approved-by", "editor", *common],
    )

    assert init_result.exit_code == 0
    assert '"state": "Draft"' in init_result.stdout
    assert run_result.exit_code == 0
    assert '"current_state": "QualityChecked"' in run_result.stdout
    assert status_result.exit_code == 0
    assert '"current_state": "QualityChecked"' in status_result.stdout
    assert '"executable_step": "approve"' in status_result.stdout
    assert '"workflow_history"' in status_result.stdout
    assert approval_result.exit_code == 0
    assert '"current_state": "Approved"' in approval_result.stdout


def test_cli_reports_invalid_workflow_command_with_a_nonzero_exit_code(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]
    runner.invoke(app, ["init", "--project", "demo", "--page", "001", *common])

    result = runner.invoke(app, ["review", "demo", "001", *common])

    assert result.exit_code == 1
    assert "executable step is 'design'" in result.stderr


def test_cli_support_command_runs_through_workflow_engine(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]
    runner.invoke(app, ["init", "--project", "demo", "--page", "001", *common])

    result = runner.invoke(app, ["continuity", "demo", "001", *common])

    assert result.exit_code == 0
    assert '"completed_step": "continuity"' in result.stdout
    assert '"current_state": "Draft"' in result.stdout


def test_cli_planning_previews_one_page_without_executing_a_step(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]
    runner.invoke(app, ["init", "--project", "demo", "--page", "001", *common])

    preview = runner.invoke(
        app,
        ["planning", "preview", "demo", "001", "--capability", "text", *common],
    )
    status = runner.invoke(app, ["status", "demo", "001", *common])
    provider = runner.invoke(app, ["planning", "provider", "--capability", "text", *common])

    assert preview.exit_code == 0
    assert '"execution_performed": false' in preview.stdout
    assert '"command": "design"' in preview.stdout
    assert status.exit_code == 0
    assert '"current_state": "Draft"' in status.stdout
    assert provider.exit_code == 0
    assert '"selection_performed": false' in provider.stdout


def test_cli_analytics_remain_read_only_for_one_page(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]
    runner.invoke(app, ["init", "--project", "demo", "--page", "001", *common])

    workflow = runner.invoke(app, ["analytics", "workflow", "demo", "001", *common])
    providers = runner.invoke(app, ["analytics", "providers", *common])
    executive = runner.invoke(app, ["analytics", "executive", "demo", "001", *common])
    status = runner.invoke(app, ["status", "demo", "001", *common])

    assert workflow.exit_code == providers.exit_code == executive.exit_code == 0
    assert '"analysis_only": true' in workflow.stdout
    assert '"optimization_performed": false' in providers.stdout
    assert '"automatic_action_taken": false' in executive.stdout
    assert '"current_state": "Draft"' in status.stdout


def test_cli_assurance_reports_reliability_without_running_a_step(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]
    runner.invoke(app, ["init", "--project", "demo", "--page", "001", *common])

    workflow = runner.invoke(app, ["assurance", "workflow", "demo", "001", *common])
    providers = runner.invoke(app, ["assurance", "providers", *common])
    dashboard = runner.invoke(app, ["assurance", "dashboard", "demo", "001", *common])
    status = runner.invoke(app, ["status", "demo", "001", *common])

    assert workflow.exit_code == providers.exit_code == dashboard.exit_code == 0
    assert '"execution_performed": false' in workflow.stdout
    assert '"governance_only": true' in providers.stdout
    assert '"automatic_release": false' in dashboard.stdout
    assert '"current_state": "Draft"' in status.stdout


def test_cli_v3_foundation_reports_remain_non_executing_for_one_page(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]
    runner.invoke(app, ["init", "--project", "demo", "--page", "001", *common])

    platform = runner.invoke(app, ["director", "platform", "--project", "demo", *common])
    creative = runner.invoke(app, ["director", "creative", "--project", "demo", *common])
    foundation = runner.invoke(app, ["director", "foundation", *common])
    intelligence = runner.invoke(app, ["director", "intelligence", "--project", "demo", *common])
    summary = runner.invoke(app, ["director", "summary", "--project", "demo", *common])
    status = runner.invoke(app, ["status", "demo", "001", *common])

    assert platform.exit_code == creative.exit_code == foundation.exit_code == 0
    assert intelligence.exit_code == summary.exit_code == status.exit_code == 0
    assert '"automatic_action_taken": false' in platform.stdout
    assert '"image_generation_invoked": false' in creative.stdout
    assert '"persistence_mutated": false' in foundation.stdout
    assert '"workflow_modified": false' in intelligence.stdout
    assert '"execution_performed": false' in summary.stdout
    assert '"current_state": "Draft"' in status.stdout


def test_cli_v3_collaboration_reports_never_run_agents_or_approve(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]
    runner.invoke(app, ["init", "--project", "demo", "--page", "001", *common])

    collaboration = runner.invoke(app, ["director", "collaboration", "--project", "demo", *common])
    knowledge = runner.invoke(app, ["director", "creative-knowledge", "--project", "demo", *common])
    intelligence = runner.invoke(app, ["director", "creative-intelligence", "--project", "demo", *common])
    review = runner.invoke(app, ["director", "review-pipeline", "--project", "demo", *common])
    status = runner.invoke(app, ["status", "demo", "001", *common])

    assert collaboration.exit_code == knowledge.exit_code == intelligence.exit_code == review.exit_code == 0
    assert '"execution_dispatched": false' in collaboration.stdout
    assert '"repository_read_only": true' in knowledge.stdout
    assert '"workflow_modified": false' in intelligence.stdout
    assert '"approval_granted": false' in review.stdout
    assert '"current_state": "Draft"' in status.stdout


def test_cli_v3_readiness_reports_do_not_deploy_or_authorize_release(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]
    runner.invoke(app, ["init", "--project", "demo", "--page", "001", *common])

    reliability = runner.invoke(app, ["director", "reliability-v3", "--project", "demo", *common])
    governance = runner.invoke(app, ["director", "creative-governance", "--project", "demo", *common])
    integrity = runner.invoke(app, ["director", "knowledge-integrity", "--project", "demo", *common])
    production = runner.invoke(app, ["director", "production-readiness", "--project", "demo", *common])
    release = runner.invoke(app, ["director", "release-dashboard", "--project", "demo", *common])
    status = runner.invoke(app, ["status", "demo", "001", *common])

    assert reliability.exit_code == governance.exit_code == integrity.exit_code == 0
    assert production.exit_code == release.exit_code == status.exit_code == 0
    assert '"automatic_action_taken": false' in reliability.stdout
    assert '"persistence_mutated": false' in governance.stdout
    assert '"persistence_mutated": false' in integrity.stdout
    assert '"deployment_performed": false' in production.stdout
    assert '"automatic_release": false' in release.stdout
    assert '"current_state": "Draft"' in status.stdout


def test_cli_v3_1_foundations_are_non_executing_and_keep_one_page_state(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]
    runner.invoke(app, ["init", "--project", "demo", "--page", "001", *common])

    collaboration = runner.invoke(
        app, ["director", "collaboration-foundation", "--project", "demo", *common]
    )
    knowledge = runner.invoke(app, ["director", "knowledge-evolution", *common])
    operations = runner.invoke(
        app, ["director", "operations-foundation", "--project", "demo", *common]
    )
    productivity = runner.invoke(app, ["director", "developer-productivity", *common])
    metrics = runner.invoke(app, ["director", "project-metrics", "--project", "demo", *common])
    status = runner.invoke(app, ["status", "demo", "001", *common])

    assert collaboration.exit_code == knowledge.exit_code == operations.exit_code == 0
    assert productivity.exit_code == metrics.exit_code == status.exit_code == 0
    assert '"approval_granted": false' in collaboration.stdout
    assert '"persistence_mutated": false' in knowledge.stdout
    assert '"automatic_action_taken": false' in operations.stdout
    assert '"filesystem_mutated": false' in productivity.stdout
    assert '"aggregation_only": true' in metrics.stdout
    assert '"current_state": "Draft"' in status.stdout


def test_cli_v3_1_insights_do_not_review_automatically_or_change_state(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]
    runner.invoke(app, ["init", "--project", "demo", "--page", "001", *common])

    review = runner.invoke(app, ["director", "creative-review", "--project", "demo", *common])
    knowledge = runner.invoke(app, ["director", "knowledge-analytics", *common])
    operations = runner.invoke(
        app, ["director", "operations-intelligence", "--project", "demo", *common]
    )
    experience = runner.invoke(app, ["director", "developer-experience", *common])
    efficiency = runner.invoke(
        app, ["director", "workflow-efficiency", "--project", "demo", *common]
    )
    status = runner.invoke(app, ["status", "demo", "001", *common])

    assert review.exit_code == knowledge.exit_code == operations.exit_code == 0
    assert experience.exit_code == efficiency.exit_code == status.exit_code == 0
    assert '"approval_granted": false' in review.stdout
    assert '"repository_port_only": true' in knowledge.stdout
    assert '"automatic_operation_started": false' in operations.stdout
    assert '"filesystem_mutated": false' in experience.stdout
    assert '"workflow_executed": false' in efficiency.stdout
    assert '"current_state": "Draft"' in status.stdout


def test_cli_v3_1_assurance_reports_do_not_approve_deploy_or_release(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]
    runner.invoke(app, ["init", "--project", "demo", "--page", "001", *common])

    governance = runner.invoke(
        app, ["director", "creative-governance-v31", "--project", "demo", *common]
    )
    knowledge = runner.invoke(app, ["director", "knowledge-reliability", *common])
    readiness = runner.invoke(
        app, ["director", "operational-readiness-v31", "--project", "demo", *common]
    )
    quality = runner.invoke(app, ["director", "release-quality", "--project", "demo", *common])
    compatibility = runner.invoke(
        app, ["director", "compatibility-validation", "--project", "demo", *common]
    )
    status = runner.invoke(app, ["status", "demo", "001", *common])

    assert governance.exit_code == knowledge.exit_code == readiness.exit_code == 0
    assert quality.exit_code == compatibility.exit_code == status.exit_code == 0
    assert '"approval_granted": false' in governance.stdout
    assert '"persistence_mutated": false' in knowledge.stdout
    assert '"deployment_performed": false' in readiness.stdout
    assert '"release_authorized": false' in quality.stdout
    assert '"breaking_change_applied": false' in compatibility.stdout
    assert '"current_state": "Draft"' in status.stdout
