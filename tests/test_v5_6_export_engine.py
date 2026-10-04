"""Contracts for the read-only v5.6 Export Engine v1."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.domain.state_machine import PageState
from manga_director.production import ExportManagerDTO, V56ExportEngineService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _metadata() -> dict[str, object]:
    return {
        "print_export": {"trim_size": "B5", "dpi": 600},
        "web_export": {"format": "webp", "width": 1440},
        "ebook_export": {"format": "epub", "reading_direction": "rtl"},
        "publishing_metadata": {"title": "Last Train", "language": "ja", "rights": "all-rights"},
    }


def _context(
    *,
    metadata: dict[str, object] | None = None,
    state: PageState = PageState.APPROVED,
    artifacts: dict[str, object] | None = None,
) -> WorkflowContext:
    return WorkflowContext(
        page={"id": "chapter-1-page-1"},
        state=state,
        artifacts=artifacts
        if artifacts is not None
        else {
            PageState.GENERATED.value: {"image_path": "page-1.png"},
            PageState.QUALITY_CHECKED.value: {"passed": True},
            PageState.STORYBOARDED.value: {"panels": []},
        },
        metadata=metadata if metadata is not None else _metadata(),
    )


def test_print_export_validation_requires_approved_quality_reviewed_generated_page() -> None:
    context = _context()
    before = context.model_dump()
    report = V56ExportEngineService().export_engine("chapter-1", context)

    assert report.planning_only is True
    assert report.manager.page_count == 1
    assert report.print_export.status == "ready"
    assert report.manager.export_performed is False
    assert context.model_dump() == before


def test_web_export_validation_requires_web_specification() -> None:
    metadata = _metadata()
    web = metadata["web_export"]
    assert isinstance(web, dict)
    web.pop("width")

    report = V56ExportEngineService().export_engine("chapter-1", _context(metadata=metadata))

    assert report.web_export.status == "needs_evidence"
    assert "Missing web export specification." in report.summary.findings


def test_ebook_export_validation_requires_ebook_specification() -> None:
    metadata = _metadata()
    ebook = metadata["ebook_export"]
    assert isinstance(ebook, dict)
    ebook.pop("reading_direction")

    report = V56ExportEngineService().export_engine("chapter-1", _context(metadata=metadata))

    assert report.ebook_export.status == "needs_evidence"
    assert "Missing eBook export specification." in report.summary.findings


def test_asset_packaging_validation_requires_generated_asset_evidence() -> None:
    report = V56ExportEngineService().export_engine(
        "chapter-1",
        _context(
            artifacts={
                PageState.QUALITY_CHECKED.value: {"passed": True},
                PageState.STORYBOARDED.value: {"panels": []},
            }
        ),
    )

    assert report.asset_packager.package_eligible is False
    assert report.asset_packager.package_created is False


def test_metadata_validation_requires_title_language_and_rights() -> None:
    metadata = _metadata()
    publishing = metadata["publishing_metadata"]
    assert isinstance(publishing, dict)
    publishing.pop("rights")

    report = V56ExportEngineService().export_engine("chapter-1", _context(metadata=metadata))

    assert report.metadata.metadata_eligible is False
    assert report.metadata.metadata_generated is False


def test_release_bundle_validation_requires_all_target_and_delivery_evidence() -> None:
    report = V56ExportEngineService().export_engine("chapter-1", _context())

    assert report.release_bundle.bundle_eligible is True
    assert report.release_bundle.bundle_created is False


def test_archive_integrity_validation_requires_delivery_eligibility_and_never_archives() -> None:
    report = V56ExportEngineService().export_engine("chapter-1", _context())

    assert report.archive.archive_eligible is True
    assert report.archive.archive_integrity_valid is True
    assert report.archive.archive_created is False


def test_export_manager_rejects_more_than_one_page() -> None:
    with pytest.raises(ValidationError):
        ExportManagerDTO(
            project_id="chapter-1",
            page_reference="chapter-1-page-1",
            current_state=PageState.APPROVED,
            page_count=2,
            generated_artifact_available=True,
            quality_review_completed=True,
            human_approval_completed=True,
            export_eligible=True,
        )


def test_export_engine_keeps_delivery_repository_and_workflow_boundaries_out() -> None:
    source = (ROOT / "src/manga_director/production/v5_6_export_engine.py").read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "manga_director.api",
        "manga_director.cli",
        "manga_director.mcp",
        "manga_director.repositories",
        "workflow.engine",
        ".execute(",
        ".advance(",
        "save(",
    ):
        assert forbidden not in source


def test_export_engine_docs_are_available() -> None:
    assets = (
        "docs/EXPORT_ENGINE.md",
        "docs/EXPORT_MANAGER.md",
        "docs/PRINT_EXPORT.md",
        "docs/WEB_EXPORT.md",
        "docs/EBOOK_EXPORT.md",
        "docs/ASSET_PACKAGER.md",
        "docs/METADATA_GENERATOR.md",
        "docs/RELEASE_BUNDLE_BUILDER.md",
        "docs/ARCHIVE_MANAGER.md",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
