"""Documentation contracts for the v6.x OSS maturity baseline."""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from email.message import Message
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERIFIER_SPEC = importlib.util.spec_from_file_location(
    "verify_release_artifacts", ROOT / "scripts" / "verify_release_artifacts.py"
)
assert VERIFIER_SPEC is not None and VERIFIER_SPEC.loader is not None
VERIFIER = importlib.util.module_from_spec(VERIFIER_SPEC)
sys.modules[VERIFIER_SPEC.name] = VERIFIER
VERIFIER_SPEC.loader.exec_module(VERIFIER)


def test_oss_governance_and_community_documents_are_available_and_linked() -> None:
    documents = (
        "CONTRIBUTING.md",
        "GOVERNANCE.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "SUPPORT.md",
        "RFC_PROCESS.md",
        "ROADMAP.md",
        "DEPRECATION_POLICY.md",
    )

    assert all((ROOT / document).is_file() for document in documents)
    for document_name in documents:
        document = ROOT / document_name
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", document.read_text(encoding="utf-8")):
            if not link.startswith(("http://", "https://", "mailto:")):
                assert (document.parent / link).exists(), f"{document}: broken link to {link}"


def test_oss_maturity_documents_preserve_v6_lts_safety_and_compatibility() -> None:
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")

    assert "exactly one Page" in contributing
    assert "StateMachine" in security
    assert "No new platform capability" in roadmap


def test_oss_ci_and_release_validation_workflows_cover_the_maintenance_baseline() -> None:
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    release = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    assert all(job in ci for job in ("static-analysis:", "test:", "frontend:", "package:", "security:"))
    for workflow in (ci, release):
        assert "python scripts/verify_release_artifacts.py historical-baseline" in workflow
        assert "python scripts/build_publication_candidate.py" in workflow
        assert "python scripts/verify_release_artifacts.py current-candidate" in workflow
        assert "build/publication-candidate/*" in workflow
    assert "python -m build" not in release
    assert "twine check dist/*" not in release


def _git(repository: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=repository, check=True, capture_output=True)


def _source_state_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    (repository / "src" / "manga_director").mkdir(parents=True)
    (repository / ".gitignore").write_text("build/\n", encoding="utf-8")
    (repository / "src" / "manga_director" / "tracked.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "test@example.invalid")
    _git(repository, "config", "user.name", "Artifact Authority Test")
    _git(repository, "add", ".")
    _git(repository, "commit", "-qm", "baseline")
    return repository


def test_source_state_binds_untracked_files_and_ignores_candidate_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _source_state_repository(tmp_path)
    monkeypatch.chdir(repository)
    baseline = VERIFIER._source_state()

    generated = repository / "build" / "publication-candidate" / "generated.txt"
    generated.parent.mkdir(parents=True)
    generated.write_text("generated\n", encoding="utf-8")
    assert VERIFIER._source_state() == baseline

    untracked = repository / "src" / "manga_director" / "untracked.py"
    untracked.write_text("VALUE = 2\n", encoding="utf-8")
    after_add = VERIFIER._source_state()
    assert after_add != baseline
    with pytest.raises(ValueError, match="stale or inconsistent provenance"):
        VERIFIER._verify_source_state(baseline)

    renamed = untracked.with_name("renamed.py")
    untracked.rename(renamed)
    after_rename = VERIFIER._source_state()
    with pytest.raises(ValueError, match="stale or inconsistent provenance"):
        VERIFIER._verify_source_state(after_add)

    renamed.write_text("VALUE = 3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="stale or inconsistent provenance"):
        VERIFIER._verify_source_state(after_rename)

    renamed.unlink()
    with pytest.raises(ValueError, match="stale or inconsistent provenance"):
        VERIFIER._verify_source_state(after_rename)

    tracked = repository / "src" / "manga_director" / "tracked.py"
    tracked.write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="stale or inconsistent provenance"):
        VERIFIER._verify_source_state(baseline)

    _git(repository, "add", "src/manga_director/tracked.py")
    _git(repository, "commit", "-qm", "head change")
    with pytest.raises(ValueError, match="stale or inconsistent provenance"):
        VERIFIER._verify_source_state(baseline)


def _metadata(
    base_requirements: list[str],
    optional_requirements: list[str],
    extras: tuple[str, ...] = ("postgresql", "api", "url"),
) -> Message:
    metadata = Message()
    metadata["Name"] = "example-package"
    metadata["Version"] = "1.0.0"
    metadata["Summary"] = "example"
    metadata["Requires-Python"] = ">=3.11"
    for extra in extras:
        metadata["Provides-Extra"] = extra
    for requirement in [*base_requirements, *optional_requirements]:
        metadata["Requires-Dist"] = requirement
    return metadata


def test_runtime_dependency_metadata_comparison_is_semantic_and_fail_closed() -> None:
    project = {
        "name": "example-package",
        "description": "example",
        "requires-python": ">=3.11",
        "dependencies": ["pydantic>=2.7,<3"],
        "optional-dependencies": {
            "postgresql": ["psycopg[binary]>=3.1,<4"],
            "api": ['marker>=1; python_version < "3.13"'],
            "url": ["urlpkg @ https://example.invalid/urlpkg-1.whl"],
        },
    }
    valid_optional = [
        'psycopg[binary]<4,>=3.1; extra == "postgresql"',
        'marker>=1; python_version < "3.13" and extra == "api"',
        'urlpkg @ https://example.invalid/urlpkg-1.whl ; extra == "url"',
    ]
    valid = _metadata(["pydantic<3,>=2.7"], valid_optional)

    assert VERIFIER._verify_metadata(valid, "1.0.0", project) == {
        "source_runtime_dependency_count": 1,
        "artifact_requires_dist_count": 4,
    }
    invalid_cases = (
        _metadata([], valid_optional),
        _metadata(["pydantic>=2.7,<3", "unexpected==1"], valid_optional),
        _metadata(["pydantic>=3"], valid_optional),
        _metadata(['pydantic>=2.7,<3; python_version < "3.12"'], valid_optional),
        _metadata(["pydantic>=2.7,<3"], [*valid_optional[:1], *valid_optional[2:]]),
        _metadata(
            ["pydantic>=2.7,<3"],
            [valid_optional[0].replace("[binary]", ""), *valid_optional[1:]],
        ),
        _metadata(
            ["pydantic>=2.7,<3"],
            [valid_optional[0].replace("[binary]", "[c]"), *valid_optional[1:]],
        ),
        _metadata(
            ["pydantic>=2.7,<3"],
            [*valid_optional, 'unexpected==1; extra == "api"'],
        ),
        _metadata(
            ["pydantic>=2.7,<3"],
            [valid_optional[0].replace(">=3.1", ">=4"), *valid_optional[1:]],
        ),
        _metadata(
            ["pydantic>=2.7,<3"],
            [valid_optional[0], 'marker>=1; extra == "api"', valid_optional[2]],
        ),
        _metadata(
            ["pydantic>=2.7,<3"],
            [valid_optional[0], valid_optional[1].replace('"3.13"', '"3.12"'), valid_optional[2]],
        ),
        _metadata(
            ["pydantic>=2.7,<3"],
            [valid_optional[0], valid_optional[1], 'urlpkg; extra == "url"'],
        ),
        _metadata(
            ["pydantic>=2.7,<3"],
            [
                valid_optional[0],
                valid_optional[1],
                'urlpkg @ https://example.invalid/urlpkg-2.whl ; extra == "url"',
            ],
        ),
    )
    for invalid in invalid_cases:
        with pytest.raises(ValueError):
            VERIFIER._verify_metadata(invalid, "1.0.0", project)


def test_compound_marker_metadata_is_canonical_and_fail_closed() -> None:
    project = {
        "name": "example-package",
        "description": "example",
        "requires-python": ">=3.11",
        "dependencies": [],
        "optional-dependencies": {
            "compound-and": [
                'and-package>=1; python_version < "3.13" and sys_platform == "win32"'
            ],
            "compound-or": [
                'or-package>=1; python_version < "3.13" or sys_platform == "win32"'
            ],
        },
    }
    valid_optional = [
        'and-package>=1; sys_platform == "win32" and extra == "compound-and" '
        'and python_version < "3.13"',
        'or-package>=1; (sys_platform == "win32" or python_version < "3.13") '
        'and extra == "compound-or"',
    ]
    valid = _metadata([], valid_optional, ("compound-and", "compound-or"))

    assert VERIFIER._verify_metadata(valid, "1.0.0", project) == {
        "source_runtime_dependency_count": 0,
        "artifact_requires_dist_count": 2,
    }
    invalid_cases = (
        _metadata(
            [],
            [
                'and-package>=1; sys_platform == "win32" and extra == "compound-and"',
                valid_optional[1],
            ],
            ("compound-and", "compound-or"),
        ),
        _metadata(
            [],
            [
                'and-package>=1; sys_platform == "linux" and extra == "compound-and" '
                'and python_version < "3.13"',
                valid_optional[1],
            ],
            ("compound-and", "compound-or"),
        ),
        _metadata(
            [],
            [
                'and-package>=1; sys_platform == "win32" and extra == "compound-and" '
                'and python_version < "3.12"',
                valid_optional[1],
            ],
            ("compound-and", "compound-or"),
        ),
        _metadata(
            [],
            [
                'and-package>=1; (sys_platform == "win32" or python_version < "3.13") '
                'and extra == "compound-and"',
                valid_optional[1],
            ],
            ("compound-and", "compound-or"),
        ),
        _metadata(
            [],
            [
                valid_optional[0],
                'or-package>=1; python_version < "3.13" and extra == "compound-or"',
            ],
            ("compound-and", "compound-or"),
        ),
        _metadata(
            [],
            [
                valid_optional[0],
                'or-package>=1; (sys_platform == "linux" or python_version < "3.13") '
                'and extra == "compound-or"',
            ],
            ("compound-and", "compound-or"),
        ),
    )
    for invalid in invalid_cases:
        with pytest.raises(ValueError):
            VERIFIER._verify_metadata(invalid, "1.0.0", project)
