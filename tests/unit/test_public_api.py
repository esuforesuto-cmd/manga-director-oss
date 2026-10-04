import tomllib
from pathlib import Path

import manga_director
from manga_director import (
    Director,
    ImageGenerator,
    Page,
    Project,
    Repository,
    WorkflowContext,
    WorkflowEngine,
)
from manga_director.domain.exceptions import StateTransitionError, WorkflowError


def test_documented_public_api_is_importable_from_package_root() -> None:
    assert Director is not None
    assert WorkflowEngine is not None
    assert WorkflowContext is not None
    assert Project is not None
    assert Page is not None
    assert ImageGenerator is not None
    assert Repository is not None


def test_director_public_facade_executes_a_workflow_step() -> None:
    result = Director.default().execute(WorkflowContext(page={"page_id": "1"}), "design")

    assert result.current_state.value == "Designed"


def test_state_transition_error_is_a_workflow_error() -> None:
    assert issubclass(StateTransitionError, WorkflowError)


def test_package_version_source_is_declared_in_release_metadata() -> None:
    project_root = Path(__file__).resolve().parents[2]
    metadata = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["dynamic"] == ["version"]
    assert metadata["tool"]["hatch"]["version"]["path"] == "src/manga_director/_version.py"
    version_source = project_root / "src" / "manga_director" / "_version.py"
    assert f'__version__ = "{manga_director.__version__}"' in version_source.read_text(
        encoding="utf-8"
    )
