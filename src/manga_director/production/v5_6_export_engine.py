"""Read-only v5.6 Export Engine v1 for one approved manga page.

The module standardizes commercial publishing readiness for print, web, and
eBook targets. It creates no files, packages, metadata records, bundles,
archives, uploads, or publication actions.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext

ExportStatus = Literal["ready", "needs_evidence"]


class ExportManagerDTO(DirectorModel):
    """One-page commercial-delivery eligibility under existing workflow gates."""

    project_id: str
    page_reference: str
    current_state: PageState
    page_count: Literal[1] = 1
    generated_artifact_available: bool
    quality_review_completed: bool
    human_approval_completed: bool
    export_eligible: bool
    export_performed: Literal[False] = False


class PrintExportDTO(DirectorModel):
    profile: Literal["print"] = "print"
    specification_available: bool
    export_eligible: bool
    status: ExportStatus
    export_performed: Literal[False] = False


class WebExportDTO(DirectorModel):
    profile: Literal["web"] = "web"
    specification_available: bool
    export_eligible: bool
    status: ExportStatus
    export_performed: Literal[False] = False


class EBookExportDTO(DirectorModel):
    profile: Literal["ebook"] = "ebook"
    specification_available: bool
    export_eligible: bool
    status: ExportStatus
    export_performed: Literal[False] = False


class AssetPackagerDTO(DirectorModel):
    asset_references: tuple[str, ...] = ()
    generated_asset_available: bool
    package_eligible: bool
    package_created: Literal[False] = False


class MetadataGeneratorDTO(DirectorModel):
    title_available: bool
    language_available: bool
    rights_available: bool
    metadata_eligible: bool
    metadata_generated: Literal[False] = False


class ReleaseBundleBuilderDTO(DirectorModel):
    print_ready: bool
    web_ready: bool
    ebook_ready: bool
    assets_ready: bool
    metadata_ready: bool
    bundle_eligible: bool
    bundle_created: Literal[False] = False


class ArchiveManagerDTO(DirectorModel):
    archive_eligible: bool
    archive_integrity_valid: bool
    archive_created: Literal[False] = False


class ExportPromptBriefDTO(DirectorModel):
    """Compact delivery brief that reuses approved evidence by key."""

    page_reference: str
    compact_instruction: str = (
        "Prepare exactly one approved page for the requested publishing target using supplied export "
        "specification, asset, and metadata evidence; do not publish or upload."
    )
    reused_context_keys: tuple[str, ...] = ()
    duplicate_context_elided: bool = True
    prompt_generated: Literal[False] = False


class CommercialPublishingSummary(DirectorModel):
    project_id: str
    page_reference: str
    standard_stages: tuple[str, ...] = (
        "export_eligibility",
        "print_export",
        "web_export",
        "ebook_export",
        "asset_packaging",
        "metadata",
        "release_bundle",
        "archive",
    )
    files_created: Literal[0] = 0
    publication_started: Literal[False] = False
    automatic_action_taken: Literal[False] = False
    findings: tuple[str, ...] = ()


class ExportEngineReport(DirectorModel):
    """Transport-neutral Export Engine v1 report for one immutable context."""

    manager: ExportManagerDTO
    print_export: PrintExportDTO
    web_export: WebExportDTO
    ebook_export: EBookExportDTO
    asset_packager: AssetPackagerDTO
    metadata: MetadataGeneratorDTO
    release_bundle: ReleaseBundleBuilderDTO
    archive: ArchiveManagerDTO
    prompt_brief: ExportPromptBriefDTO
    summary: CommercialPublishingSummary
    planning_only: Literal[True] = True


class V56ExportEngineService:
    """Build delivery-readiness reports without exporting or publishing content."""

    def export_engine(self, project_id: str, context: WorkflowContext) -> ExportEngineReport:
        page_reference = _page_reference(context)
        print_specification = _mapping(_context_value(context, "print_export"))
        web_specification = _mapping(_context_value(context, "web_export"))
        ebook_specification = _mapping(_context_value(context, "ebook_export"))
        publishing_metadata = _mapping(_context_value(context, "publishing_metadata"))
        generated_artifact_available = PageState.GENERATED.value in context.artifacts
        quality_review_completed = PageState.QUALITY_CHECKED.value in context.artifacts
        human_approval_completed = context.state is PageState.APPROVED and quality_review_completed
        export_eligible = (
            generated_artifact_available and quality_review_completed and human_approval_completed
        )
        print_specification_available = _print_specification_valid(print_specification)
        web_specification_available = _web_specification_valid(web_specification)
        ebook_specification_available = _ebook_specification_valid(ebook_specification)
        print_ready = export_eligible and print_specification_available
        web_ready = export_eligible and web_specification_available
        ebook_ready = export_eligible and ebook_specification_available
        asset_references = tuple(sorted(str(name) for name in context.artifacts))
        package_eligible = generated_artifact_available and bool(asset_references)
        title_available = bool(publishing_metadata.get("title"))
        language_available = bool(publishing_metadata.get("language"))
        rights_available = bool(publishing_metadata.get("rights"))
        metadata_eligible = title_available and language_available and rights_available
        bundle_eligible = (
            print_ready and web_ready and ebook_ready and package_eligible and metadata_eligible
        )
        archive_integrity_valid = bundle_eligible and len(asset_references) == len(
            set(asset_references)
        )
        findings = _findings(
            export_eligible=export_eligible,
            print_ready=print_ready,
            web_ready=web_ready,
            ebook_ready=ebook_ready,
            package_eligible=package_eligible,
            metadata_eligible=metadata_eligible,
            bundle_eligible=bundle_eligible,
            archive_integrity_valid=archive_integrity_valid,
        )

        return ExportEngineReport(
            manager=ExportManagerDTO(
                project_id=project_id,
                page_reference=page_reference,
                current_state=context.state,
                generated_artifact_available=generated_artifact_available,
                quality_review_completed=quality_review_completed,
                human_approval_completed=human_approval_completed,
                export_eligible=export_eligible,
            ),
            print_export=PrintExportDTO(
                specification_available=print_specification_available,
                export_eligible=print_ready,
                status=_status(print_ready),
            ),
            web_export=WebExportDTO(
                specification_available=web_specification_available,
                export_eligible=web_ready,
                status=_status(web_ready),
            ),
            ebook_export=EBookExportDTO(
                specification_available=ebook_specification_available,
                export_eligible=ebook_ready,
                status=_status(ebook_ready),
            ),
            asset_packager=AssetPackagerDTO(
                asset_references=asset_references,
                generated_asset_available=generated_artifact_available,
                package_eligible=package_eligible,
            ),
            metadata=MetadataGeneratorDTO(
                title_available=title_available,
                language_available=language_available,
                rights_available=rights_available,
                metadata_eligible=metadata_eligible,
            ),
            release_bundle=ReleaseBundleBuilderDTO(
                print_ready=print_ready,
                web_ready=web_ready,
                ebook_ready=ebook_ready,
                assets_ready=package_eligible,
                metadata_ready=metadata_eligible,
                bundle_eligible=bundle_eligible,
            ),
            archive=ArchiveManagerDTO(
                archive_eligible=bundle_eligible,
                archive_integrity_valid=archive_integrity_valid,
            ),
            prompt_brief=ExportPromptBriefDTO(
                page_reference=page_reference,
                reused_context_keys=tuple(
                    key
                    for key, value in (
                        ("print_export", print_specification),
                        ("web_export", web_specification),
                        ("ebook_export", ebook_specification),
                        ("publishing_metadata", publishing_metadata),
                    )
                    if value
                ),
            ),
            summary=CommercialPublishingSummary(
                project_id=project_id,
                page_reference=page_reference,
                findings=findings,
            ),
        )


def _print_specification_valid(specification: Mapping[str, object]) -> bool:
    return bool(specification.get("trim_size")) and bool(specification.get("dpi"))


def _web_specification_valid(specification: Mapping[str, object]) -> bool:
    return bool(specification.get("format")) and bool(specification.get("width"))


def _ebook_specification_valid(specification: Mapping[str, object]) -> bool:
    return bool(specification.get("format")) and bool(specification.get("reading_direction"))


def _context_value(context: WorkflowContext, key: str) -> object:
    return context.metadata.get(key) or context.page.get(key)


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _page_reference(context: WorkflowContext) -> str:
    value = context.page.get("id")
    return str(value) if value is not None else "current-page"


def _status(ready: bool) -> ExportStatus:
    return "ready" if ready else "needs_evidence"


def _findings(
    *,
    export_eligible: bool,
    print_ready: bool,
    web_ready: bool,
    ebook_ready: bool,
    package_eligible: bool,
    metadata_eligible: bool,
    bundle_eligible: bool,
    archive_integrity_valid: bool,
) -> tuple[str, ...]:
    findings: list[str] = []
    for name, available in (
        ("approved generated page with completed quality review", export_eligible),
        ("print export specification", print_ready),
        ("web export specification", web_ready),
        ("eBook export specification", ebook_ready),
        ("asset package evidence", package_eligible),
        ("publishing metadata", metadata_eligible),
        ("release bundle evidence", bundle_eligible),
        ("archive integrity evidence", archive_integrity_valid),
    ):
        if not available:
            findings.append(f"Missing {name}.")
    return tuple(findings)
